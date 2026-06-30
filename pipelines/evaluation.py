from zenml import pipeline
from scripts.evaluating import evaluate


@pipeline
def evaluating(
    is_dummy: bool = False,
):
    evaluate(is_dummy=is_dummy)
