from prometheus_client import Counter

task_operations_total = Counter(
    "task_operations_total",
    "Task operations by operation and result",
    ["operation", "result"],
)
