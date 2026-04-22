def recommend(rules, user_items):
    recs = set()

    for _, row in rules.iterrows():
        if set(row["antecedents"]).issubset(user_items):
            recs.update(row["consequents"])

    return list(recs - set(user_items))
