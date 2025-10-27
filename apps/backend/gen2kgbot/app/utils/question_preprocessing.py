import spacy


def extract_relevant_entities_spacy(question: str) -> list[str]:
    """
    Extract relevant entities from the NL question

    Args:
        question (str): Natural Language question

    Returns:
        list: entities extracted from the question
    """

    # Load the pre-trained spaCy model (en_core_web_sm is a small English model)
    # Try models in order of preference
    try:
        nlp = spacy.load("en_core_sci_lg")  # YT works best
    except OSError:
        try:
            nlp = spacy.load("en_core_web_lg")
        except OSError:
            nlp = spacy.load("en_core_web_sm")  # Fallback to small model

    # Process the question through the spaCy pipeline
    # TODO: model should be loaded only once, not at each invokation
    doc = nlp(question)
    relevant_entities = [doc.text for doc in doc.ents]

    # Filter extracted entities by type
    # relevant_entities = []
    # relevant_entity_types = ['PERSON', 'ORG', 'GPE', 'LOC', 'DATE', 'TIME']
    # for ent in doc.ents:
    #     print(ent.label_)
    #     if ent.label_ in relevant_entity_types:
    #         relevant_entities.append(ent.text)

    return relevant_entities


# # Example use
# question = "What protein targets does donepezil (CHEBI_53289) inhibit with an IC50 less than 10 µM?"
# print("Extracted relevant entities:", extract_relevant_entities_spacy(question))
