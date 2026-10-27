"""TESTING ONLY (docs/development/test-doubles.md): a LangSmith client that records runs instead of sending them."""

import copy


class RecordingLangSmithClient:
    """Stands in for `langsmith.Client`: keeps every run the RunTree API posts or patches, after the same
    hide_inputs / hide_outputs / hide_metadata hooks the real client applies."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.runs: dict[str, dict] = {}

    def _hide(self, run: dict) -> dict:
        run = copy.deepcopy(run)
        for key, hook in (("inputs", "hide_inputs"), ("outputs", "hide_outputs")):
            if run.get(key) is not None and callable(self.kwargs.get(hook)):
                run[key] = self.kwargs[hook](run[key])
        metadata = (run.get("extra") or {}).get("metadata")
        if metadata is not None and callable(self.kwargs.get("hide_metadata")):
            run["extra"]["metadata"] = self.kwargs["hide_metadata"](metadata)
        return run

    def create_run(self, **run):
        self.runs[str(run["id"])] = self._hide(run)

    def update_run(self, run_id, **run):
        stored = self.runs.setdefault(str(run_id), {"id": run_id})
        stored.update({key: value for key, value in self._hide(run).items() if value is not None})

    def flush(self):
        pass

    def _construct_run_url(self, run):
        return f"https://smith.test/runs/{run.id}"

    def named(self, name: str) -> list[dict]:
        return [run for run in self.runs.values() if run.get("name") == name]

    def children(self, parent_id) -> list[dict]:
        return [run for run in self.runs.values() if str(run.get("parent_run_id")) == str(parent_id)]
