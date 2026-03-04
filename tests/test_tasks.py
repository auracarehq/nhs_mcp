from tasks import create_task, get_task, update_task


def test_create_and_get():
    task = create_task()
    assert task.status == "pending"
    assert task.done == 0
    retrieved = get_task(task.task_id)
    assert retrieved is task


def test_update():
    task = create_task()
    update_task(task.task_id, status="running", done=5, total=10, message="halfway")
    assert task.status == "running"
    assert task.done == 5
    assert task.total == 10
    assert task.message == "halfway"
    assert task.updated_at != ""


def test_get_missing():
    assert get_task("nonexistent") is None


def test_to_dict():
    task = create_task()
    d = task.to_dict()
    assert "task_id" in d
    assert d["status"] == "pending"
