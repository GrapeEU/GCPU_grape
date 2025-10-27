#!/usr/bin/env python3
"""
Generate embeddings for Grape medical knowledge graphs

This script generates textual descriptions and embeddings for all 4 Grape medical KGs:
- grape_demo: General medical conditions
- grape_hearing: Hearing & Tinnitus disorders
- grape_psychiatry: Mental health & Depression
- grape_unified: All KGs + cross-domain alignments

Usage:
    python scripts/generate_grape_embeddings.py

Requirements:
    - GraphDB running on localhost:7200 with all 4 repositories loaded
    - Ollama running with nomic-embed-text model
    - gen2kgbot submodule present in apps/backend/
"""

import sys
import os
from pathlib import Path

# Add gen2kgbot to path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "apps" / "backend"
GEN2KGBOT_DIR = BACKEND_DIR / "gen2kgbot"

if not GEN2KGBOT_DIR.exists():
    print(f"❌ ERROR: gen2kgbot not found at {GEN2KGBOT_DIR}")
    print("   Please ensure gen2kgbot submodule is initialized:")
    print("   git submodule update --init --recursive")
    sys.exit(1)

sys.path.insert(0, str(GEN2KGBOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

# Now import gen2kgbot modules
try:
    from app.preprocessing.gen_descriptions import (
        make_classes_description,
        make_properties_description,
        get_classes_with_instances,
        save_to_txt
    )
    from app.preprocessing.compute_embeddings import compute_embeddings_from_file
    import app.utils.config_manager as config
    from app.utils.logger_manager import setup_logger
except ImportError as e:
    print(f"❌ ERROR: Failed to import gen2kgbot modules: {e}")
    print("   Make sure gen2kgbot dependencies are installed:")
    print("   cd apps/backend && uv pip install -r requirements.txt")
    sys.exit(1)

logger = setup_logger(__name__, __file__)

# Grape KG configurations
GRAPE_KGS = [
    {
        "short_name": "grape_demo",
        "full_name": "Grape Demo Medical Knowledge Graph",
        "endpoint": "http://localhost:7200/repositories/demo",
        "description": "General medical conditions including Asthma, Anxiety, and Hypertension with their symptoms and risk factors",
        "prefixes": {
            "exmed": "http://example.org/medical/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "schema": "http://schema.org/",
            "skos": "http://www.w3.org/2004/02/skos/core#"
        }
    },
    {
        "short_name": "grape_hearing",
        "full_name": "Grape Hearing & Tinnitus Knowledge Graph",
        "endpoint": "http://localhost:7200/repositories/hearing",
        "description": "ENT disorders focusing on Tinnitus, Hearing Loss, Hyperacusis and their symptoms, treatments, and risk factors",
        "prefixes": {
            "exhear": "http://example.org/hearing/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "schema": "http://schema.org/",
            "skos": "http://www.w3.org/2004/02/skos/core#"
        }
    },
    {
        "short_name": "grape_psychiatry",
        "full_name": "Grape Psychiatry & Mental Health Knowledge Graph",
        "endpoint": "http://localhost:7200/repositories/psychiatry",
        "description": "Mental health disorders including Major Depression, Anxiety, PTSD with symptoms and interventions",
        "prefixes": {
            "expsych": "http://example.org/psychiatry/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "schema": "http://schema.org/",
            "skos": "http://www.w3.org/2004/02/skos/core#"
        }
    },
    {
        "short_name": "grape_unified",
        "full_name": "Grape Unified Medical Knowledge Graph",
        "endpoint": "http://localhost:7200/repositories/unified",
        "description": "Integrated medical knowledge graph combining all domains (general, ENT, psychiatry) with cross-domain alignments using owl:sameAs and owl:equivalentClass",
        "prefixes": {
            "exmed": "http://example.org/medical/",
            "exhear": "http://example.org/hearing/",
            "expsych": "http://example.org/psychiatry/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "schema": "http://schema.org/",
            "skos": "http://www.w3.org/2004/02/skos/core#"
        }
    }
]

# Embedding model configuration
EMBEDDING_MODEL = "nomic-embed-text_faiss@local"


def configure_gen2kgbot_for_kg(kg_config):
    """
    Configure gen2kgbot config manager for a specific Grape KG

    Args:
        kg_config: KG configuration dict
    """
    logger.info(f"Configuring gen2kgbot for {kg_config['short_name']}")

    # Update global config
    config.config["kg_short_name"] = kg_config["short_name"]
    config.config["kg_full_name"] = kg_config["full_name"]
    config.config["kg_sparql_endpoint_url"] = kg_config["endpoint"]
    config.config["ontologies_sparql_endpoint_url"] = kg_config["endpoint"]
    config.config["kg_description"] = kg_config["description"]
    config.config["prefixes"] = kg_config["prefixes"]

    logger.debug(f"Configuration updated:")
    logger.debug(f"  - Endpoint: {kg_config['endpoint']}")
    logger.debug(f"  - Data dir: {config.get_kg_data_directory()}")


def generate_descriptions_for_kg(kg_config):
    """
    Generate textual descriptions for a KG's classes and properties

    Args:
        kg_config: KG configuration dict

    Returns:
        tuple: (classes_file, properties_file, classes_with_instances_file)
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"STEP 1: Generating descriptions for {kg_config['short_name']}")
    logger.info(f"{'='*70}")

    # Configure gen2kgbot
    configure_gen2kgbot_for_kg(kg_config)

    # File paths
    preprocessing_dir = config.get_preprocessing_directory()
    classes_file = preprocessing_dir / "classes_description.txt"
    properties_file = preprocessing_dir / "properties_description.txt"
    classes_with_instances_file = preprocessing_dir / "classes_with_instances_description.txt"

    # 1. Generate class descriptions
    logger.info("Retrieving class descriptions from SPARQL endpoint...")
    try:
        classes_descriptions = make_classes_description()
        save_to_txt(classes_file, classes_descriptions)
        logger.info(f"✅ Saved {len(classes_descriptions)} class descriptions to {classes_file}")
    except Exception as e:
        logger.error(f"❌ Failed to generate class descriptions: {e}")
        raise

    # 2. Generate property descriptions
    logger.info("Retrieving property descriptions from SPARQL endpoint...")
    try:
        properties_descriptions = make_properties_description()
        save_to_txt(properties_file, properties_descriptions)
        logger.info(f"✅ Saved {len(properties_descriptions)} property descriptions to {properties_file}")
    except Exception as e:
        logger.error(f"❌ Failed to generate property descriptions: {e}")
        raise

    # 3. Get classes with instances
    logger.info("Retrieving classes with instances...")
    try:
        classes_with_instances = get_classes_with_instances()

        # Filter classes_description to keep only classes with instances
        classes_description_filtered = []
        for c in classes_descriptions:
            if c[0] in classes_with_instances:
                classes_description_filtered.append(c)

        save_to_txt(classes_with_instances_file, classes_description_filtered)
        logger.info(f"✅ Saved {len(classes_description_filtered)} classes with instances to {classes_with_instances_file}")
    except Exception as e:
        logger.error(f"❌ Failed to filter classes with instances: {e}")
        raise

    return classes_file, properties_file, classes_with_instances_file


def generate_embeddings_for_kg(kg_config, classes_file):
    """
    Generate embeddings for a KG's class descriptions

    Args:
        kg_config: KG configuration dict
        classes_file: Path to classes_with_instances_description.txt
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"STEP 2: Generating embeddings for {kg_config['short_name']}")
    logger.info(f"{'='*70}")

    # Configure gen2kgbot
    configure_gen2kgbot_for_kg(kg_config)

    # Get embedding model config
    embed_config = config.get_embedding_model_config_by_name(EMBEDDING_MODEL)
    vector_db_name = embed_config["vector_db"]

    # Output directory for embeddings
    embeddings_dir = (
        config.get_embeddings_directory(vector_db_name)
        / config.get_class_embeddings_subdir()
    )

    logger.info(f"Embedding model: {EMBEDDING_MODEL}")
    logger.info(f"Vector DB: {vector_db_name}")
    logger.info(f"Input file: {classes_file}")
    logger.info(f"Output dir: {embeddings_dir}")

    # Generate embeddings
    try:
        compute_embeddings_from_file(EMBEDDING_MODEL, str(classes_file), str(embeddings_dir))
        logger.info(f"✅ Embeddings generated successfully for {kg_config['short_name']}")
    except Exception as e:
        logger.error(f"❌ Failed to generate embeddings: {e}")
        raise


def preprocess_kg(kg_config):
    """
    Full preprocessing pipeline for a Grape KG

    Args:
        kg_config: KG configuration dict
    """
    logger.info(f"\n{'#'*70}")
    logger.info(f"PREPROCESSING: {kg_config['full_name']}")
    logger.info(f"{'#'*70}")

    try:
        # Step 1: Generate descriptions
        classes_file, properties_file, classes_with_instances_file = generate_descriptions_for_kg(kg_config)

        # Step 2: Generate embeddings (using classes_with_instances only)
        generate_embeddings_for_kg(kg_config, classes_with_instances_file)

        logger.info(f"\n✅ COMPLETED: {kg_config['short_name']}")
        logger.info(f"   - Classes: {classes_file}")
        logger.info(f"   - Properties: {properties_file}")
        logger.info(f"   - Embeddings: {config.get_embeddings_directory('faiss') / config.get_class_embeddings_subdir()}")

        return True
    except Exception as e:
        logger.error(f"\n❌ FAILED: {kg_config['short_name']} - {e}")
        return False


def check_prerequisites():
    """
    Check that all prerequisites are met

    Returns:
        bool: True if all checks pass
    """
    logger.info("Checking prerequisites...")

    checks = []

    # 1. Check GraphDB connectivity
    logger.info("1. Checking GraphDB connectivity...")
    try:
        import requests
        for kg in GRAPE_KGS:
            # GraphDB: use /size endpoint to check connectivity
            size_endpoint = f"{kg['endpoint']}/size"
            response = requests.get(size_endpoint, timeout=5)
            if response.status_code == 200:
                triple_count = response.text.strip()
                logger.info(f"   ✅ {kg['short_name']}: Connected ({triple_count} triples)")
                checks.append(True)
            else:
                logger.error(f"   ❌ {kg['short_name']}: HTTP {response.status_code}")
                checks.append(False)
    except Exception as e:
        logger.error(f"   ❌ GraphDB check failed: {e}")
        logger.error(f"   Make sure GraphDB is running: docker-compose -f docker-compose.graphdb.yml up -d")
        checks.append(False)

    # 2. Check Ollama + embedding model
    logger.info("2. Checking Ollama + nomic-embed-text model...")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            if any("nomic-embed-text" in name for name in model_names):
                logger.info(f"   ✅ Ollama + nomic-embed-text: Available")
                checks.append(True)
            else:
                logger.error(f"   ❌ nomic-embed-text model not found")
                logger.error(f"   Install with: ollama pull nomic-embed-text")
                checks.append(False)
        else:
            logger.error(f"   ❌ Ollama API returned HTTP {response.status_code}")
            checks.append(False)
    except Exception as e:
        logger.error(f"   ❌ Ollama check failed: {e}")
        logger.error(f"   Make sure Ollama is running: brew services start ollama")
        checks.append(False)

    # 3. Check gen2kgbot dependencies
    logger.info("3. Checking gen2kgbot dependencies...")
    try:
        import faiss
        import langchain
        import spacy
        logger.info(f"   ✅ Dependencies: Installed")
        checks.append(True)
    except ImportError as e:
        logger.error(f"   ❌ Missing dependency: {e}")
        logger.error(f"   Install with: cd apps/backend && uv pip install -r requirements.txt")
        checks.append(False)

    return all(checks)


def main():
    """Main preprocessing pipeline"""

    print("\n" + "="*70)
    print("🍇 GRAPE - Knowledge Graph Embeddings Generator")
    print("="*70)

    # Check prerequisites
    if not check_prerequisites():
        logger.error("\n❌ Prerequisites check failed. Please fix the issues above.")
        sys.exit(1)

    logger.info("\n✅ All prerequisites met. Starting preprocessing...")

    # Process each KG
    results = []
    for kg_config in GRAPE_KGS:
        success = preprocess_kg(kg_config)
        results.append((kg_config["short_name"], success))

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    for kg_name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {kg_name}")

    success_count = sum(1 for _, s in results if s)
    total_count = len(results)

    print(f"\nResults: {success_count}/{total_count} KGs processed successfully")
    print("="*70)

    if success_count == total_count:
        print("\n🎉 All embeddings generated successfully!")
        print("\nNext steps:")
        print("  1. Test connection: python scripts/test_graphdb_connection.py")
        print("  2. Test embeddings: python scripts/test_gen2kgbot_integration.py")
        print("  3. Implement scenarios: apps/backend/scenarios/scenario_*.py")
        sys.exit(0)
    else:
        print("\n⚠️  Some KGs failed to process. Check logs above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
