from langchain_core.globals import set_verbose
from loguru import logger

from .retriever import ContextRetriever
from services.infrastructure.opik_config.opik_utils import configure_opik

if __name__ == "__main__":
    configure_opik()
    set_verbose(True)

    query = """
        My name is Maxime Labonne.

        Could you draft a LinkedIn post discussing Q-learning?
        I'm particularly interested in:
            - how Q-learning works
            - reinforcement learning
            - training an RL agent.
        """

    retriever = ContextRetriever(mock=False)
    documents = retriever.search(query, k=9)

    logger.info("Retrieved documents:")
    for rank, document in enumerate(documents):
        logger.info(f"{rank + 1}: {document}")
