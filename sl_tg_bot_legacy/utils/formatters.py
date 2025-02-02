def round_km(value):
    """Округляет километры до 2 знаков после запятой"""
    return round(float(value), 2) if value is not None else 0.0 