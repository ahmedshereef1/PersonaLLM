from pathlib import Path

from zenml import pipeline
from zenml.client import Client

from scripts.export_data import serialize_artifact, to_json


@pipeline
def export_artifact_to_json(
    artifact_names: list[str], output_dir: Path = Path("output")
) -> None:
    for artifact_name in artifact_names:
        artifact_version = Client().get_artifact_version(
            name_id_or_prefix=artifact_name
        )

        artifact_data = artifact_version.load()

        data = serialize_artifact(artifact=artifact_data, artifact_name=artifact_name)

        to_json(data=data, to_file=output_dir / f"{artifact_name}.json")
