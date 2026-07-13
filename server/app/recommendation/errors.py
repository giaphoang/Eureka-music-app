class RecommendationError(RuntimeError):
    status_code = 503


class RecommendationUnavailable(RecommendationError):
    pass


class RecommendationStaleIndex(RecommendationError):
    pass


class RecommendationConfigError(RecommendationError):
    pass
