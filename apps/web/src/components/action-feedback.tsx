export function ActionFeedback({ message, failed }: { message: string; failed: boolean }) {
  return message ? <p className={`action-feedback ${failed ? "failed" : ""}`} role={failed ? "alert" : "status"}>{message}</p> : null;
}
