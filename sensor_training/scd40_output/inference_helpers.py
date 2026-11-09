HORIZON_MINUTES = 5
import numpy as np
import pandas as pd
SIGNALS = ['co2_ppm', 'temperature_c', 'humidity_percent']
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


def predict_latest(history, trained_models, feature_columns):
    x = build_features(history).iloc[[-1]][feature_columns]
    if x.isna().any(axis=None):
        raise ValueError('Butuh 31 menit terakhir yang lengkap sebelum memprediksi.')
    result = {'prediction_time': history.index[-1].isoformat(),
              'target_time': (history.index[-1]+pd.Timedelta(minutes=HORIZON_MINUTES)).isoformat()}
    for target, model in trained_models.items():
        result[target] = float(x[target].iloc[0] if model is None else model.predict(x)[0])
    return result

