from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser
from loguru import logger


class ListPydanticOutputParser(PydanticOutputParser):
    def _parse_obj(self, obj):
        logger.info(f"Parser received type: {type(obj)}")

        if obj is None:
            logger.warning("Received null JSON response")
            return []

        if isinstance(obj, list):
            parsed = []

            for i, item in enumerate(obj):
                try:
                    parsed.append(
                        super(ListPydanticOutputParser, self)._parse_obj(item)
                    )
                except OutputParserException as e:
                    logger.warning(f"Invalid item #{i}: {item}\n{e}")

            logger.info(f"Parsed {len(parsed)}/{len(obj)} valid samples")
            return parsed

        try:
            return super(ListPydanticOutputParser, self)._parse_obj(obj)
        except OutputParserException as e:
            logger.warning(f"Invalid object: {obj}\n{e}")
            return []
