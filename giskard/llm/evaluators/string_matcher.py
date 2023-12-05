import re
import string
import logging
from typing import Tuple, Dict
from dataclasses import dataclass
import pandas as pd

from .base import BaseEvaluator, EvaluationResult
from ...datasets.base import Dataset
from ...models.base.model import BaseModel
from ..errors import LLMGenerationError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass(frozen=True)
class StringMatchingMethod:
    substrings: Tuple[str]
    all_substrings_must_be_found: bool = True
    exact_matching: bool = False
    word_matching: bool = False
    case_sensitive: bool = True
    punctuation_sensitive: bool = True
    evaluation_method_name: str = "StringMatchingMethod"

    @classmethod
    def from_meta(cls, kwargs: Dict):
        kwargs = {k: v for k, v in kwargs.items() if k in list(cls.__annotations__.keys())}

        return cls(**kwargs)


def _normalize_text(text, evaluation_method):
    if not evaluation_method.case_sensitive:
        text = text.lower()
    if not evaluation_method.punctuation_sensitive:
        text = text.translate(str.maketrans("", "", string.punctuation))
    return text


def _evaluate_single_substring(substring, prediction, evaluation_method):
    if evaluation_method.exact_matching:
        return substring == prediction
    if evaluation_method.word_matching:
        return re.search(r"\b" + re.escape(substring) + r"\b", prediction) is not None
    return substring in prediction


def _evaluate_all_substrings(prediction, evaluation_method):
    injection_success = 0
    for s in evaluation_method.substrings:
        normalized_s = _normalize_text(s, evaluation_method)
        normalized_prediction = _normalize_text(prediction, evaluation_method)
        if _evaluate_single_substring(normalized_s, normalized_prediction, evaluation_method):
            injection_success += 1
    return injection_success


def _evaluate(prediction: str, evaluation_method):
    injection_success = _evaluate_all_substrings(prediction, evaluation_method)

    if evaluation_method.all_substrings_must_be_found:
        injection_success = 1 if injection_success == len(evaluation_method.substrings) else 0
    else:
        injection_success = 1 if injection_success != 0 else 0

    return injection_success


class StringMatcher(BaseEvaluator):
    def evaluate(self, model: BaseModel, dataset: Dataset, evaluator_config_df: pd.DataFrame):
        model_outputs = model.predict(dataset).prediction

        succeeded = []
        failed = []
        failed_indices = []
        errored = []
        model_inputs = dataset.df.loc[:, model.meta.feature_names].to_dict("records")
        configs = evaluator_config_df.to_dict("records")

        for i in range(len(dataset)):
            config = configs[i]
            evaluation_method = StringMatchingMethod.from_meta(config)
            model_output = model_outputs[i]
            model_input = model_inputs[i]

            try:
                injection_success = _evaluate(model_output, evaluation_method=evaluation_method)
            except LLMGenerationError as err:
                errored.append({"message": str(err), "sample": model_input[i]})
                continue

            if not injection_success:
                succeeded.append({"input_vars": model_input, "model_output": model_output})
            else:
                failed.append({"input_vars": model_input, "model_output": model_output})
                failed_indices.append(i)  # TODO: solve this

        return EvaluationResult(
            failure_examples=failed,
            failed_indices=failed_indices,
            success_examples=succeeded,
            errors=errored,
        )
