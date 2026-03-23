"""dm+d domain configuration."""

# Snowstorm (SNOMED CT UK Drug Extension) — same base used by snomed domain
SNOWSTORM_BASE = "https://snowstorm.ihtsdotools.org/snowstorm/snomed-ct"
UK_BRANCH_ENCODED = "MAIN%2FSNOMEDCT-UK"

# ECL expression for all medicinal products
MEDICINAL_PRODUCT_ECL = "<763158003"

# NHS Terminology Server FHIR endpoint (public read, no auth)
NHS_TS_FHIR_BASE = "https://ontology.nhs.uk/production1/fhir"
DMD_SYSTEM = "https://dmd.nhs.uk"
