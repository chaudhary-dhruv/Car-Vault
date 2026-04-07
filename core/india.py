from decimal import Decimal, ROUND_HALF_UP


USD_TO_INR = Decimal("83.00")
MPG_TO_KMPL = Decimal("0.425144")
MPH_TO_KMPH = Decimal("1.60934")
ZERO_TO_SIXTY_TO_ZERO_TO_HUNDRED = Decimal("1.0356")
CUFT_TO_LITERS = Decimal("28.3168")


def quantize(value, places="0.1"):
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def format_inr(value):
    amount = int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    digits = str(amount)
    if len(digits) <= 3:
        return f"{sign}₹{digits}"
    last_three = digits[-3:]
    remaining = digits[:-3]
    groups = []
    while len(remaining) > 2:
        groups.insert(0, remaining[-2:])
        remaining = remaining[:-2]
    if remaining:
        groups.insert(0, remaining)
    formatted = ",".join(groups + [last_three])
    return f"{sign}₹{formatted}"


def usd_to_inr(value):
    return Decimal(value) * USD_TO_INR


def mpg_to_kmpl(value):
    return quantize(Decimal(value) * MPG_TO_KMPL)


def mph_to_kmph(value):
    return quantize(Decimal(value) * MPH_TO_KMPH, "1")


def zero_to_hundred_time(value):
    return quantize(Decimal(value) * ZERO_TO_SIXTY_TO_ZERO_TO_HUNDRED)


def cuft_to_liters(value):
    return quantize(Decimal(value) * CUFT_TO_LITERS, "1")
