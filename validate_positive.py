
def validate_positive(**named_vals):
    for name, val in named_vals.items():
        if val <= 0:
            raise ValueError(f"'{name}' debe ser positivo, no {val}")
