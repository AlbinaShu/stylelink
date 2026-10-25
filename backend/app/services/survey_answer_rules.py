"""Business rules shared by survey persistence and research exports."""
DEFINITE_FIT = {"perfect", "small", "large"}
UNTRIED_FIT = {"in_transit", "not_tried"}


def survey_outcomes(answer):
    """Unknown and untried states never count as failed fit."""
    tried = answer.fit_result in DEFINITE_FIT | {"unknown"}
    received = answer.order_placed == "yes" and answer.fit_result not in {None, "in_transit"}
    return {
        "received": received,
        "tried": received and tried,
        "fit_evaluable": received and answer.fit_result in DEFINITE_FIT,
        "fit_success": received and answer.fit_result == "perfect",
        "tried_size": getattr(answer, "tried_size", None) if tried else None,
    }
