# Golden requirements for the design diversity report (Story 20.1)

Short static-site requirements with **no brand colours or fonts**, so the design direction alone decides the look.
`manifest.json` names the brief drafted several times (`sameBrief`) and the pairs of similar businesses whose
designs should still differ. Used by `make design-diversity` (`agent-api/scripts/design_diversity.py`).

`dynamic` lists app requirements (Story 20.4, epic D12): they are drafted in dynamic mode and their directions get
the same difference test; with `--screenshots` every page of each direction, data pages included, is built and
checked on the mock API.
