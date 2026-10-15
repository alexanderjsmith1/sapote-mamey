from pathlib import Path
from mamey.comparators.antismash_ingest import ingest_comparator_inputs

def test_ingestion_preserves_preexisting_fixed_extraction_directory(tmp_path):
    output = tmp_path / "output"
    prior = output / "_extracted_comparators"
    prior.mkdir(parents=True)
    source = prior / "unique.txt"
    source.write_text("irreplaceable input")
    ingest_comparator_inputs([], output)
    assert source.is_file()
    assert source.read_text() == "irreplaceable input"
    assert not list(output.glob("_extracted_comparators_*"))
