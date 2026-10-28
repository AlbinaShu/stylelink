"""Outcomes for the recommended-size survey; historical answers retain their scope."""
DEFINITE_FIT = {"perfect", "small", "large"}


def survey_outcomes(answer):
    scope = getattr(answer, "fit_scope", None) == "recommended_only"
    tried = answer.fit_result in DEFINITE_FIT | {"unknown"}
    received = scope and answer.order_placed == "yes" and answer.fit_result not in {None, "in_transit", "not_ordered"}
    return {
        "received": received,
        "tried": received and tried,
        "fit_evaluable": received and answer.fit_result in DEFINITE_FIT,
        "fit_success": received and answer.fit_result == "perfect",
        "tried_size": "recommended" if scope and tried else None,
    }
