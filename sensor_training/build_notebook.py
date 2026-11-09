"""Build the standalone Colab notebook. No application/database changes."""
import json
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
cells = []


def cell(kind, source):
    item = dict(cell_type=kind, metadata={}, source=dedent(source).strip() + "\n")
    if kind == "code":
        item.update(execution_count=None, outputs=[])
    cells.append(item)


cell("markdown", """
# Training prediksi SCD40: suhu dan CO₂ ruang kerja

Notebook mandiri untuk Google Colab, cukup runtime **CPU**. Jalankan sel dari atas ke bawah.
Default langsung membuat **30 hari data dummy, satu sampel per menit (43.200 baris)**.
Untuk memakai CSV yang disediakan, pilih `DATA_MODE = 'upload'`, lalu unggah `scd40_dummy.csv`.

**Target:** suhu (°C) dan CO₂ (ppm) **5 menit setelah waktu pengamatan terakhir**.
Input hanya riwayat CO₂, suhu, kelembapan, dan waktu. Model sensor terpisah dari YOLOv11.

**Makna akurasi:** MAE/RMSE mengukur selisih prediksi dari pembacaan sensor di masa depan.
Ini bukan kalibrasi atau pembuktian akurasi fisik SCD40. Kalibrasi memerlukan pengukuran
serentak dari alat referensi. Hasil dummy hanya menunjukkan alur simulasi, bukan performa ruang nyata.
Notebook tidak menetapkan kategori nyaman/aman karena kriteria ruangan belum ditentukan.

## 1. Persiapan
Pilih Runtime > Run all. GPU tidak diperlukan. Output disimpan dalam folder `scd40_output`.
""")
cell("code", """
%pip -q install numpy pandas scikit-learn matplotlib joblib
""")
cell("code", """
from pathlib import Path
import json, zipfile, platform
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sklearn, joblib
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from IPython.display import display

SEED = 42
DATA_MODE = 'dummy'  # 'dummy' atau 'upload'
HORIZON_MINUTES = 5
TIMEZONE = 'Asia/Jakarta'
SIGNALS = ['co2_ppm', 'temperature_c', 'humidity_percent']
TARGETS = ['temperature_c', 'co2_ppm']
# Toleransi contoh eksperimen, BUKAN spesifikasi sensor atau standar kesehatan.
TOLERANCES = {'temperature_c': 0.5, 'co2_ppm': 100.0}
OUT = Path('scd40_output')
OUT.mkdir(exist_ok=True)
assert isinstance(HORIZON_MINUTES, int) and HORIZON_MINUTES > 0
""")
cell("markdown", """
## 2. Data dummy atau unggahan data asli
Generator memakai asumsi sederhana: jam kerja, variasi penghuni, pergantian ventilasi/AC,
dan gangguan acak. Variabel tersebut hanya digunakan untuk simulasi, tidak menjadi input model.
Koefisien simulasi tidak berasal dari pengukuran SCD40 atau pemodelan fisik terkalibrasi.
Seed tetap membuat contoh dapat diulang. Tanggal Oktober 2026 adalah tanggal simulasi.

CSV wajib memiliki `timestamp`, `co2_ppm`, `temperature_c`, `humidity_percent`.
Gunakan timestamp ISO 8601 dengan zona waktu, misalnya `2026-10-01T08:00:00+07:00`.
Kolom opsional `source` harus seluruhnya `synthetic` atau seluruhnya `scd40`.
Satu file hanya untuk **satu sensor di satu ruangan**. Jangan mencampur dummy dengan data asli.
""")
cell("code", """
def generate_dummy(days=30, seed=SEED):
    rng = np.random.default_rng(seed)
    times = pd.date_range('2026-10-01', periods=days*1440, freq='min', tz=TIMEZONE)
    co2, temp, humidity = 450.0, 26.0, 58.0
    occupants, ventilation, cooling = 0, 0.05, False
    rows = []
    for i, stamp in enumerate(times):
        working = stamp.dayofweek < 5 and 8 <= stamp.hour < 18
        if i % 30 == 0:
            occupants = int(rng.integers(1, 13)) if working else int(rng.choice([0, 0, 0, 1]))
            ventilation = float(rng.choice([0.025, 0.05, 0.09]))
            cooling = bool(working and rng.random() < 0.85)
        outside = 29 + 3*np.sin(2*np.pi*(stamp.hour + stamp.minute/60 - 9)/24)
        co2 += 2.2*occupants - ventilation*(co2-425) + rng.normal(0, 3)
        equilibrium = (24.0 if cooling else outside) + 0.04*occupants
        temp += 0.025*(equilibrium-temp) + rng.normal(0, 0.025)
        humidity += 0.02*((48 if cooling else 64)-humidity) + rng.normal(0, 0.15)
        rows.append((stamp.isoformat(), round(max(380, co2+rng.normal(0, 6)), 1),
                     round(temp+rng.normal(0, 0.04), 2),
                     round(np.clip(humidity+rng.normal(0, 0.2), 20, 90), 2), 'synthetic'))
    return pd.DataFrame(rows, columns=['timestamp', *SIGNALS, 'source'])

if DATA_MODE == 'dummy':
    raw = generate_dummy()
    raw.to_csv(OUT/'scd40_dummy.csv', index=False)
elif DATA_MODE == 'upload':
    from google.colab import files
    uploaded = files.upload()
    names = [n for n in uploaded if n.lower().endswith('.csv')]
    if len(names) != 1:
        raise ValueError('Unggah tepat satu CSV sensor.')
    raw = pd.read_csv(names[0])
else:
    raise ValueError('DATA_MODE harus dummy atau upload.')
display(raw.head())
print('Jumlah baris sumber:', len(raw))
""")
cell("markdown", """
## 3. Validasi dan penyeragaman interval
Data diurutkan berdasarkan waktu. Sampel lima detik boleh diunggah: dirata-ratakan menjadi
satu menit **berlabel ujung interval**, hanya memakai sampel pada/sebelum timestamp tersebut.
Duplikat timestamp, waktu tanpa zona, data campuran, atau angka tidak valid ditolak.
Batas pemeriksaan angka mengikuti penerimaan data pada project, bukan klaim rentang akurasi alat.
Menit kosong dibiarkan kosong. Tidak ada interpolasi, pengisian mundur, atau penggunaan masa depan.
Baris training yang melewati celah riwayat/target dikeluarkan.
""")
cell("code", """
def prepare_data(frame):
    missing = set(['timestamp', *SIGNALS]) - set(frame.columns)
    if missing:
        raise ValueError(f'Kolom belum tersedia: {sorted(missing)}')
    frame = frame.copy()
    if 'source' in frame:
        sources = set(frame['source'].astype(str).str.lower().str.strip())
        if len(sources) != 1 or not sources <= {'synthetic', 'scd40'}:
            raise ValueError('source harus seragam: synthetic atau scd40; jangan campur.')
        source = next(iter(sources))
    else:
        source = 'unknown'
        print('Asal data tidak ditandai. Verifikasi sendiri bahwa ini data sensor asli.')
    text = frame['timestamp'].astype(str)
    if not text.str.contains(r'(?:Z|[+-]\\d{2}:\\d{2})$', regex=True).all():
        raise ValueError('Setiap timestamp harus memuat zona waktu: +07:00 atau Z.')
    stamp = pd.to_datetime(text, utc=True, errors='coerce', format='mixed')
    if stamp.isna().any() or stamp.duplicated().any():
        raise ValueError('Timestamp tidak valid atau duplikat; perbaiki CSV terlebih dahulu.')
    values = frame[SIGNALS].apply(pd.to_numeric, errors='coerce')
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError('Angka sensor kosong/tidak valid ditemukan pada sumber.')
    valid = (values.co2_ppm.between(1, 40000) & values.temperature_c.between(-40, 125)
             & values.humidity_percent.between(0, 100))
    if not valid.all():
        raise ValueError('Nilai di luar batas pemeriksaan input project.')
    values.index = pd.DatetimeIndex(stamp).tz_convert(TIMEZONE)
    values = values.sort_index()
    if values.index[-1] - values.index[0] > pd.Timedelta(days=366):
        raise ValueError('Gunakan maksimum satu tahun per eksperimen notebook ini.')
    minute = values.resample('1min', closed='right', label='right').mean()
    # Jangan membuat waktu inferensi di masa depan dari bucket terakhir yang belum selesai.
    minute = minute.loc[minute.index <= values.index[-1]]
    return minute, source

minute, DATA_SOURCE = prepare_data(raw)
print('Asal data:', DATA_SOURCE, '| Interval:', minute.index.min(), 'sampai', minute.index.max())
print('Menit tanpa pembacaan:', int(minute.isna().any(axis=1).sum()))
display(minute.describe().round(2))
""")
cell("markdown", """
## 4. Fitur masa lalu dan pemisahan waktu
Fitur: nilai saat ini, lag 1/5/10/30 menit, rata-rata dan simpangan baku 5/15/30 menit,
perubahan lima menit, serta jam/hari. Semua dihitung hanya dari informasi yang sudah tersedia.
Target adalah pembacaan tepat `HORIZON_MINUTES` ke depan.

Pembagian berdasarkan waktu: 70% awal training, 15% berikutnya validasi, 15% terakhir test.
Baris dengan target melewati batas split dibuang agar label training tidak masuk periode validasi/test.
Test mensimulasikan prediksi berulang tiap menit dengan pengamatan terbaru yang sudah tiba.
Ini bukan prediksi seluruh periode test dari satu titik awal.
""")
cell("code", """
def build_features(data):
    features = pd.DataFrame(index=data.index)
    for column in SIGNALS:
        series = data[column]
        features[column] = series
        for lag in [1, 5, 10, 30]:
            features[f'{column}_lag{lag}'] = series.shift(lag)
        for window in [5, 15, 30]:
            features[f'{column}_mean{window}'] = series.rolling(window).mean()
            features[f'{column}_std{window}'] = series.rolling(window).std()
        features[f'{column}_delta5'] = series - series.shift(5)
    hour = data.index.hour + data.index.minute/60
    features['hour_sin'] = np.sin(2*np.pi*hour/24)
    features['hour_cos'] = np.cos(2*np.pi*hour/24)
    features['weekday_sin'] = np.sin(2*np.pi*data.index.dayofweek/7)
    features['weekday_cos'] = np.cos(2*np.pi*data.index.dayofweek/7)
    complete_history = data.notna().all(axis=1).rolling(31).sum().eq(31)
    return features.where(complete_history, np.nan)

features = build_features(minute)
labels = minute[TARGETS].shift(-HORIZON_MINUTES)
target_time = pd.Series(minute.index + pd.Timedelta(minutes=HORIZON_MINUTES), index=minute.index)
complete_future = (minute.notna().all(axis=1).rolling(HORIZON_MINUTES).sum()
                   .shift(-HORIZON_MINUTES).eq(HORIZON_MINUTES))
usable = features.notna().all(axis=1) & labels.notna().all(axis=1) & complete_future
cut1 = minute.index[int(len(minute)*0.70)]
cut2 = minute.index[int(len(minute)*0.85)]
masks = {'train': usable & (target_time < cut1),
         'validation': usable & (minute.index >= cut1) & (target_time < cut2),
         'test': usable & (minute.index >= cut2)}
for name, mask in masks.items():
    if mask.sum() < 100:
        raise ValueError(f'{name}: terlalu sedikit baris lengkap. Gunakan beberapa hari data kontinu.')
    print(name, int(mask.sum()), features.index[mask][0], features.index[mask][-1])
assert target_time[masks['train']].max() < features.index[masks['validation']].min()
assert target_time[masks['validation']].max() < features.index[masks['test']].min()
print('Baris tidak dapat digunakan (riwayat, celah, atau target):', int((~usable).sum()))
""")
cell("markdown", """
## 5. Training dan memilih model berdasarkan validasi
Tiga kandidat untuk setiap target: **persistence** (nilai saat ini), **Ridge**, dan
**HistGradientBoosting**. MAE validasi terendah menentukan pilihan per target.
Tidak ada jaminan model kompleks mengalahkan persistence. Bila persistence menang, itulah hasilnya.
Early stopping acak dinonaktifkan. StandardScaler Ridge hanya dipelajari dari training.
""")
cell("code", """
candidates = {
    'persistence': None,
    'ridge': make_pipeline(StandardScaler(), Ridge(alpha=10.0)),
    'hist_gradient_boosting': HistGradientBoostingRegressor(
        max_iter=120, max_leaf_nodes=15, learning_rate=0.07,
        l2_regularization=2.0, early_stopping=False, random_state=SEED)
}
train_mask, val_mask, test_mask = (masks[k] for k in ['train', 'validation', 'test'])
validation_rows, selected = [], {}
for target in TARGETS:
    scores = {}
    for name, estimator in candidates.items():
        if estimator is None:
            pred = features.loc[val_mask, target].to_numpy()
        else:
            model = clone(estimator).fit(features.loc[train_mask], labels.loc[train_mask, target])
            pred = model.predict(features.loc[val_mask])
        mae = mean_absolute_error(labels.loc[val_mask, target], pred)
        scores[name] = mae
        validation_rows.append({'target': target, 'model': name, 'validation_mae': mae})
    selected[target] = min(scores, key=scores.get)
validation_results = pd.DataFrame(validation_rows)
display(validation_results.round(4))
print('Pilihan per target:', selected)
""")
cell("markdown", """
## 6. Evaluasi test yang belum dipakai memilih model
Setelah pilihan dibekukan, model dilatih ulang pada data sebelum periode test, dengan
target tetap sebelum batas test. Test hanya dipakai untuk laporan akhir.

- **MAE:** rata-rata besar kesalahan; satuan °C atau ppm, lebih kecil lebih baik.
- **RMSE:** lebih menekankan kesalahan besar, satuan sama.
- **R²:** dibandingkan prediksi konstan rata-rata target test; bisa negatif, bukan persen akurasi.
- **Dalam toleransi (%):** proporsi prediksi dengan galat ≤ 0,5 °C atau ≤ 100 ppm secara default.
  Toleransi ini pilihan eksperimen yang bisa diedit, bukan spesifikasi SCD40.
- **Perbaikan MAE (%):** dibandingkan persistence; negatif berarti lebih buruk.

Metrik dummy tidak boleh dilaporkan sebagai akurasi sensor atau akurasi di ruangan nyata.
""")
cell("code", """
fit_mask = usable & (target_time < cut2)
models, metric_rows = {}, []
test_predictions = pd.DataFrame({'prediction_time': features.index[test_mask],
                                 'target_time': target_time[test_mask].to_numpy()})
for target in TARGETS:
    name = selected[target]
    model = None if candidates[name] is None else clone(candidates[name]).fit(
        features.loc[fit_mask], labels.loc[fit_mask, target])
    models[target] = model
    actual = labels.loc[test_mask, target].to_numpy()
    baseline = features.loc[test_mask, target].to_numpy()
    prediction = baseline if model is None else model.predict(features.loc[test_mask])
    baseline_mae = mean_absolute_error(actual, baseline)
    for method, pred in [('persistence', baseline), ('selected: '+name, prediction)]:
        mae = mean_absolute_error(actual, pred)
        metric_rows.append(dict(source=DATA_SOURCE, target=target, method=method,
            mae=mae, rmse=np.sqrt(mean_squared_error(actual, pred)), r2=r2_score(actual, pred),
            tolerance=TOLERANCES[target], within_tolerance_pct=100*np.mean(np.abs(actual-pred)<=TOLERANCES[target]),
            improvement_mae_pct=100*(baseline_mae-mae)/baseline_mae if baseline_mae>0 else None))
    test_predictions[target+'_actual'] = actual
    test_predictions[target+'_predicted'] = prediction
    test_predictions[target+'_baseline'] = baseline
metrics = pd.DataFrame(metric_rows)
display(metrics.round(4))
if DATA_SOURCE != 'scd40':
    print('HASIL SIMULASI / SUMBER BELUM TERVERIFIKASI. Bukan validasi ruangan nyata.')

fig, axes = plt.subplots(2, 1, figsize=(13, 7), constrained_layout=True)
view = test_predictions.tail(360)
for ax, target, unit in zip(axes, TARGETS, ['°C', 'ppm']):
    for suffix, title, color in [('actual','Pembacaan target','#244835'),
                                  ('predicted','Prediksi','#699c7b'),
                                  ('baseline','Persistence','#bd9348')]:
        ax.plot(view.target_time, view[target+'_'+suffix], label=title, color=color, linewidth=1.3)
    ax.set_title(f'{target}: prediksi {HORIZON_MINUTES} menit ke depan ({DATA_SOURCE})')
    ax.set_ylabel(unit); ax.grid(alpha=0.2); ax.legend(loc='upper left')
fig.savefig(OUT/'prediksi_test.png', dpi=160)
plt.show()
""")
cell("markdown", """
## 7. Contoh prediksi dari riwayat terbaru
Ini contoh inferensi, bukan tambahan skor evaluasi. Memerlukan minimal 31 menit riwayat
kontinu dengan tiga kolom sensor yang sama. Hasil prediksi tidak menjamin kondisi nyaman/aman.
""")
cell("code", """
def predict_latest(history, trained_models, feature_columns):
    x = build_features(history).iloc[[-1]][feature_columns]
    if x.isna().any(axis=None):
        raise ValueError('Butuh 31 menit terakhir yang lengkap sebelum memprediksi.')
    result = {'prediction_time': history.index[-1].isoformat(),
              'target_time': (history.index[-1]+pd.Timedelta(minutes=HORIZON_MINUTES)).isoformat()}
    for target, model in trained_models.items():
        result[target] = float(x[target].iloc[0] if model is None else model.predict(x)[0])
    return result

example = predict_latest(minute, models, list(features.columns))
display(pd.DataFrame([example]))
""")
cell("markdown", """
## 8. Simpan dan unduh hasil
ZIP berisi model, konfigurasi fitur, hasil validasi/test, grafik, contoh prediksi, versi library,
dan kode pembentukan fitur/inferensi. Model dilatih hanya sebelum periode test.
Hanya muat file joblib yang Anda buat atau percaya karena pemuatan dapat menjalankan kode.
Model ini belum dihubungkan ke dashboard Flask. Jangan mengganti bobot YOLO `.pt` dengan file ini.
""")
cell("code", """
metadata = dict(data_source=DATA_SOURCE, horizon_minutes=HORIZON_MINUTES, frequency='1min',
    timezone=TIMEZONE, required_history_minutes=31, signals=SIGNALS, targets=TARGETS,
    feature_columns=list(features.columns), selected_models=selected, tolerances=TOLERANCES,
    train_validation_boundary=cut1.isoformat(), test_boundary=cut2.isoformat(),
    random_seed=SEED, python=platform.python_version(), sklearn=sklearn.__version__,
    numpy=np.__version__, pandas=pd.__version__,
    limitation='Synthetic results do not establish real-room performance or physical sensor accuracy.')
joblib.dump({'models': models, 'metadata': metadata}, OUT/'scd40_forecast.joblib')
(OUT/'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
(OUT/'contoh_prediksi.json').write_text(json.dumps(example, indent=2), encoding='utf-8')
validation_results.to_csv(OUT/'hasil_validasi.csv', index=False)
metrics.to_csv(OUT/'metrik_test.csv', index=False)
test_predictions.to_csv(OUT/'prediksi_test.csv', index=False)
archive_path = Path('hasil_training_scd40.zip')
with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in OUT.iterdir():
        if path.is_file():
            archive.write(path, path.name)
print('Tersimpan:', archive_path.resolve())
try:
    from google.colab import files
except ImportError:
    print('Di luar Colab: ambil ZIP dari folder kerja.')
else:
    files.download(str(archive_path))
""")
cell("markdown", """
## 9. Beralih ke data SCD40 asli
1. Simpan riwayat waktu, CO₂, suhu, dan kelembapan dari satu sensor/ruangan ke CSV.
2. Gunakan timestamp berzona waktu dan `source=scd40`. Jangan menyertakan data mode demo dashboard.
3. Kumpulkan beberapa minggu dengan variasi kondisi ruang, lalu pilih `DATA_MODE='upload'`.
4. Jalankan ulang semua sel. Laporkan MAE dalam °C/ppm, horizon, tanggal test, dan hasil persistence.
5. Uji pada hari baru sebelum mempertimbangkan integrasi prediksi ke dashboard.

Project menerima data melalui `/api/scd40` dan menyimpan pembacaan baru pada tabel
`sensor_readings`. Buka bagian Dataset sensor di dashboard untuk mengunduh CSV asli.
Riwayat sebelum fitur pencatatan dipasang tidak tersedia. Timestamp CSV adalah waktu penerimaan
server, bukan waktu ukur internal alat. Gunakan satu ESP32/sensor per instalasi saat ini.
Notebook tidak mengubah server, database, atau firmware. Data dummy tersedia untuk latihan.
""")

# Include exact reusable feature/inference definitions in the model archive, without inspect.getsource
# (which is unreliable for interactive notebook cells).
feature_source = next(
    c['source'].split('features = build_features(minute)')[0] for c in cells if c['source'].startswith('def build_features'))
predict_source = next(c['source'].split('example = predict_latest')[0] for c in cells if c['source'].startswith('def predict_latest'))
export_cell = next(c for c in cells if c['source'].startswith('metadata = dict'))
helper_source = "import numpy as np\nimport pandas as pd\nSIGNALS = " + repr(['co2_ppm', 'temperature_c', 'humidity_percent']) + "\n"
helper_source += feature_source + '\n' + predict_source
export_cell['source'] = export_cell['source'].replace("archive_path = Path", "(OUT/'inference_helpers.py').write_text('HORIZON_MINUTES = '+str(HORIZON_MINUTES)+'\\n' + " + repr(helper_source) + ", encoding='utf-8')\narchive_path = Path")
notebook = dict(cells=cells, metadata={'colab': {'name': 'SmartOffice_Colab_Training_SCD40.ipynb'},
    'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
    'language_info': {'name': 'python', 'version': '3.12'}}, nbformat=4, nbformat_minor=5)
for i, c in enumerate(cells):
    c['id'] = f'scd40-{i:02d}'
(ROOT/'SmartOffice_Colab_Training_SCD40.ipynb').write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding='utf-8')
print('Notebook created.')
