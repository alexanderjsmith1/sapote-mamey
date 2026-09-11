import copy
import pytest
from mamey.class_architecture import siderophore_evidence_projection as project

def fixture():
 identity="TEST-001 / contig_0001 / region001 / BGC001"
 locus=dict(strain="TEST-001",full_node="contig_0001",region="region001",bgc_alias="BGC001",exact_identity=identity,source_member_sha256="a"*64,population_sha256="b"*64,population="fixture",taxonomy_state="UNBOUND",products=[],cds_count=1)
 gene=dict(exact_identity=identity,source_member_sha256="a"*64,gene_order=0,protein_sha256="c"*64,membership="EXACT_REGION",transport_groups=["ABC"],cassette_groups=[])
 return locus,[gene],[],{}

def test_transport_only_never_synthesis():
 l,g,r,f=fixture();x=project(l,g,r,f)
 assert x["chemistry"]=="unresolved" and x["route"]=="unresolved"
 assert x["biosynthesis_state"]=="NO_SELECTED_OWNER_CALL_NOT_BIOLOGICAL_ABSENCE"
 assert x["production"]==x["secretion"]==x["activity"]=="unknown"

def test_route_independent_of_chemistry():
 l,g,r,f=fixture();l["products"]=["NI-siderophore"]
 x=project(l,g,r,f);assert x["route"]=="NIS" and x["chemistry"]=="unresolved"
 l["products"].append("NRP-metallophore");x=project(l,g,r,f)
 assert x["route"]=="unresolved" and x["route_candidates"]==["NIS","NRPS"]

def test_reference_chemistry_not_transferred():
 l,g,r,f=fixture();r=[dict(exact_identity=l["exact_identity"],family_name="reference")]
 f={"reference":dict(chemistry="hydroxamate",route="NRPS",citations=["primary-fixture"])}
 x=project(l,g,r,f);assert x["chemistry"]=="unresolved" and x["route"]=="unresolved"
 assert x["references"][0]["reference_chemistry"]=="hydroxamate"

def test_broad_enzyme_and_iron_cassette_remain_unresolved():
 l,g,r,f=fixture();g[0].update(product="isochorismate synthase monooxygenase IucA",cassette_groups=["siderophore_metallophore"])
 x=project(l,g,r,f);assert x["chemistry"]==x["route"]=="unresolved"
 assert x["biosynthesis_state"]=="IRON_CASSETTE_CONTEXT_ONLY"

@pytest.mark.parametrize("field,value",[("exact_identity","wrong"),("source_member_sha256","d"*64),("membership","BOUNDARY_CONTEXT"),("protein_sha256","bad")])
def test_wrong_gene_and_boundary_refused(field,value):
 l,g,r,f=fixture();g[0][field]=value
 with pytest.raises(ValueError):project(l,g,r,f)

@pytest.mark.parametrize("field,value",[("full_node",""),("population_sha256","bad"),("taxonomy_state","inferred")])
def test_identity_population_taxonomy_refused(field,value):
 l,g,r,f=fixture();l[field]=value
 with pytest.raises(ValueError):project(l,g,r,f)

def test_duplicate_gene_refused():
 l,g,r,f=fixture();g.append(copy.deepcopy(g[0]))
 with pytest.raises(ValueError):project(l,g,r,f)

def test_missing_products_not_zero():
 l,g,r,f=fixture();del l["products"]
 with pytest.raises(ValueError):project(l,g,r,f)


def test_missing_roster_not_no_call():
 l,g,r,f=fixture()
 with pytest.raises(ValueError):project(l,[],r,f)
