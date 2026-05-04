def recommend(rules, user_items):
    results = []

    for _, row in rules.iterrows():
        if set(row["antecedents"]).issubset(user_items):
            results.append(
                {
                    "item": list(row["consequents"])[0],
                    "because": list(row["antecedents"]),
                    "confidence": float(row["confidence"]),
                    "lift": float(row["lift"]),
                }
            )

    return results
