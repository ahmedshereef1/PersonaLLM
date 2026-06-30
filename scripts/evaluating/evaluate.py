from zenml import step
from services.model.evaluation.modal_runner import run_evaluation


@step
def evaluate(
    is_dummy: bool = False,
) -> None:
    run_evaluation(
        is_dummy=is_dummy,
    )
