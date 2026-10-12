#!/usr/bin/env python3
"""Calculate integer bid candidates with Decimal; never mutates merchant data."""

import argparse
import json
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR, localcontext


def calculate(target_text, discount_text, current_text=None):
    values = [target_text, discount_text]
    if current_text is not None:
        values.append(current_text)
    try:
        parsed = [Decimal(value) for value in values]
    except InvalidOperation as exc:
        raise ValueError("target, discount and current must be decimal numbers") from exc
    if not all(value.is_finite() for value in parsed):
        raise ValueError("all values must be finite")
    target, discount = parsed[:2]
    if target <= 0 or target != target.to_integral_value():
        raise ValueError("target must be a positive integer take-home price")
    if not 0 < discount <= 10:
        raise ValueError("discount must satisfy 0 < discount <= 10; 8 means 8折")
    current = parsed[2] if current_text is not None else None
    if current is not None and (current <= 0 or current != current.to_integral_value()):
        raise ValueError("current must be a positive integer bid")
    # Finite decimal multiplication must remain exact before taking the ceiling.
    precision = max(50, sum(len(value.as_tuple().digits) + abs(value.as_tuple().exponent)
                            for value in parsed) + 20)
    with localcontext() as ctx:
        ctx.prec = precision
        rate = discount / Decimal("10")
        bid = (target / rate).to_integral_value(rounding=ROUND_FLOOR)
        takehome = (bid * rate).to_integral_value(rounding=ROUND_CEILING)
        if takehome != target:
            raise ValueError("integer bid candidate does not produce the target")
        result = {
            "target": int(target),
            "target_ends_in_9": int(target) % 10 == 9,
            "discount": str(discount),
            "rate": str(rate),
            "candidate_bid": int(bid),
            "candidate_takehome": int(takehome),
            "candidate_verified": True,
            "calculation_only": True,
        }
        if current is not None:
            current_takehome = (current * rate).to_integral_value(rounding=ROUND_CEILING)
            minus_one = current - Decimal("1")
            minus_one_takehome = ((minus_one * rate).to_integral_value(rounding=ROUND_CEILING)
                                 if minus_one > 0 else None)
            result.update({
                "current_bid": int(current),
                "current_takehome": int(current_takehome),
                "current_ends_in_9": int(current_takehome) % 10 == 9,
                "current_matches_target": current_takehome == target,
                "minus_one_bid": int(minus_one) if minus_one > 0 else None,
                "minus_one_takehome": int(minus_one_takehome) if minus_one_takehome is not None else None,
                "minus_one_matches_target": minus_one_takehome == target,
                "candidate_change": int(bid - current),
            })
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Known positive integer take-home target T")
    parser.add_argument("--discount", required=True, help="Discount E; 8 means rate 0.8")
    parser.add_argument("--current", help="Existing positive integer bid")
    args = parser.parse_args()
    try:
        result = calculate(args.target, args.discount, args.current)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
