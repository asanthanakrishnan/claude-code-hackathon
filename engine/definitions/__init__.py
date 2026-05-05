from .v1 import calculate as v1
from .v2 import calculate as v2
from .v3 import calculate as v3
from .v4 import calculate as v4

REGISTRY = {
    "v1": v1,
    "v2": v2,
    "v3": v3,
    "v4": v4,
}

SUMMARIES = {
    "v1": "Logo Churn — customers lost / customers at period start. 30-day grace period. Downgrades excluded.",
    "v2": "Gross Revenue Churn (cancellations only) — MRR lost from cancellations / MRR at period start. 30-day grace period. Downgrades excluded.",
    "v3": "Gross Revenue Churn (with downgrades) — MRR lost from cancellations + downgrades >20% / MRR at period start. Calendar-month boundary.",
    "v4": "Net Revenue Churn — (MRR lost - expansion MRR gained) / MRR at period start. Calendar-month boundary.",
}
