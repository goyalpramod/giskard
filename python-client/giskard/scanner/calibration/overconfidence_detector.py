from typing import Sequence
import numpy as np
import pandas as pd

from ...ml_worker.testing.registry.slicing_function import SlicingFunction
from ...models.base import BaseModel
from ...datasets import Dataset
from ..decorators import detector
from ..common.loss_based_detector import LossBasedDetector
from .issues import CalibrationIssue, CalibrationIssueInfo, OverconfidenceIssue
from ..logger import logger


@detector(name="overconfidence", tags=["overconfidence", "classification"])
class OverconfidenceDetector(LossBasedDetector):
    def __init__(self, threshold=0.10, p_threshold=None, method="tree"):
        self.threshold = threshold
        self.p_threshold = p_threshold
        self.method = method

    @property
    def _numerical_slicer_method(self):
        return self.method

    def run(self, model: BaseModel, dataset: Dataset):
        if not model.is_classification:
            raise ValueError("Overconfidence bias detector only works for classification models.")

        return super().run(model, dataset)

    def _calculate_loss(self, model: BaseModel, dataset: Dataset) -> pd.DataFrame:
        true_target = dataset.df.loc[:, dataset.target].values
        pred = model.predict(dataset)
        label2id = {label: n for n, label in enumerate(model.meta.classification_labels)}

        # Empirical cost associated to overconfidence
        p_max = pred.probabilities
        p_true_label = np.array([pred.raw[n, label2id[label]] for n, label in enumerate(true_target)])

        loss_values = p_max - p_true_label
        mask = loss_values > 0

        return pd.DataFrame({self.LOSS_COLUMN_NAME: loss_values[mask]}, index=dataset.df.index[mask])

    def _find_issues(
        self,
        slices: Sequence[SlicingFunction],
        model: BaseModel,
        dataset: Dataset,
        meta: pd.DataFrame,
    ) -> Sequence[CalibrationIssue]:
        # Add the loss column to the dataset
        dataset_with_meta = Dataset(
            dataset.df.join(meta, how="left"),
            target=dataset.target,
            column_types=dataset.column_types,
        )
        # For performance
        dataset_with_meta._load_metadata_from_instance(dataset.column_meta)

        p_threshold = self.p_threshold or _default_overconfidence_threshold(model)
        logger.debug(f"{self.__class__.__name__}: Using overconfidence threshold = {p_threshold}")

        reference_rate = (dataset_with_meta.df[self.LOSS_COLUMN_NAME].dropna() > p_threshold).mean()

        issues = []
        for slice_fn in slices:
            sliced_dataset = dataset_with_meta.slice(slice_fn)

            slice_rate = (sliced_dataset.df[self.LOSS_COLUMN_NAME].dropna() > p_threshold).mean()
            fail_idx = sliced_dataset.df[(sliced_dataset.df[self.LOSS_COLUMN_NAME] > p_threshold)].index
            relative_delta = (slice_rate - reference_rate) / reference_rate

            if relative_delta > self.threshold:
                level = "major" if relative_delta > 2 * self.threshold else "medium"
                issues.append(
                    OverconfidenceIssue(
                        model,
                        dataset,
                        level,
                        CalibrationIssueInfo(
                            slice_fn=slice_fn,
                            slice_size=len(sliced_dataset),
                            metric_value_slice=slice_rate,
                            metric_value_reference=reference_rate,
                            loss_values=meta[self.LOSS_COLUMN_NAME],
                            fail_idx=fail_idx,
                            threshold=self.threshold,
                        ),
                    )
                )

        return issues


def _default_overconfidence_threshold(model: BaseModel) -> float:
    n = len(model.meta.classification_labels)
    return 1 / (3e-1 * (n - 2) + 2 - 1e-3 * (n - 2) ** 2)
