import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="AI Nutrition Coach", page_icon="🥗")

# background gradient styling
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(to right, #ffb6d9, #dcd0ff);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# load the dataset
df = pd.read_csv("nutrition_clean.csv")
df["food_name"] = df["food_name"].str.lower().str.strip()

# recommended daily intake values for an average adult
RDA = {
    "calories"   : 2000,
    "protein_g"  : 50,
    "carbs_g"    : 275,
    "fat_g"      : 78,
    "fiber_g"    : 28,
    "sugar_g"    : 50,
    "sodium_mg"  : 2300,
    "calcium_mg" : 1000,
    "iron_mg"    : 18
}

# classify a food as Low, Medium, or High calorie based on its calorie value
def classify_calorie_level(cal):
    if cal < 100:
        return "Low"
    elif cal <= 300:
        return "Medium"
    else:
        return "High"

# suggest top 3 foods from the dataset that are high in a given nutrient
def suggest_foods_for_nutrient(nutrient, exclude_list):
    suggestions = (
        df[~df["food_name"].isin(exclude_list)]
        .nlargest(3, nutrient)[["food_name", "category", nutrient]]
    )
    return suggestions

# app title and description
st.title("🥗 AI Nutrition Coach")
st.markdown("Type a food name or log your full day of meals to get personalized nutrition feedback.")

# create two tabs
tab1, tab2 = st.tabs(["🔍 Food Lookup", "📋 Daily Meal Logger"])


# TAB 1: FOOD LOOKUP
with tab1:
    st.subheader("Search a Food Item")

    # user types a food name
    food_input = st.text_input("Enter food name (e.g. banana, chicken breast, oatmeal cooked)")

    # user selects quantity and unit
    col_qty, col_unit = st.columns(2)
    with col_qty:
        quantity = st.number_input("Amount", min_value=1, value=100, step=10)
    with col_unit:
        unit = st.selectbox("Unit", ["grams", "plates (250g)", "cups (240g)", "pieces (150g)"])

    # convert the selected unit to grams
    unit_to_grams = {
        "grams"         : 1,
        "plates (250g)" : 250,
        "cups (240g)"   : 240,
        "pieces (150g)" : 150
    }
    actual_grams = quantity * unit_to_grams[unit]

    # multiplier scales the per-100g CSV values to actual grams consumed
    multiplier = actual_grams / 100

    if food_input:
        food_input = food_input.lower().strip()

        # try exact match first, then partial match
        result = df[df["food_name"] == food_input]
        if result.empty:
            result = df[df["food_name"].str.contains(food_input, na=False)]

        if result.empty:
            st.error(f"'{food_input}' not found in the database. Try a different name.")
        else:
            row = result.iloc[0]

            # calculate actual nutrition based on serving size
            actual_calories = round(row["calories"] * multiplier, 1)
            level = classify_calorie_level(actual_calories)
            color = {"Low": "green", "Medium": "orange", "High": "red"}[level]

            st.success(f"Found: **{row['food_name'].title()}** — {actual_grams}g serving")

            # show nutrition in 2 rows of 3 columns
            col1, col2, col3 = st.columns(3)
            col1.metric("Calories",  f"{actual_calories} kcal")
            col2.metric("Protein",   f"{round(row['protein_g'] * multiplier, 1)} g")
            col3.metric("Carbs",     f"{round(row['carbs_g']   * multiplier, 1)} g")

            col4, col5, col6 = st.columns(3)
            col4.metric("Fat",       f"{round(row['fat_g']     * multiplier, 1)} g")
            col5.metric("Fiber",     f"{round(row['fiber_g']   * multiplier, 1)} g")
            col6.metric("Category",  row["category"])

            st.markdown(f"**Calorie Level:** :{color}[{level}]")
            st.caption(f"All values calculated for {actual_grams}g ({quantity} {unit})")

            # bar chart showing nutrient breakdown
            nutrients = ["protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g"]
            values    = [round(row[n] * multiplier, 1) for n in nutrients]
            labels    = ["Protein", "Carbs", "Fat", "Fiber", "Sugar"]

            fig, ax = plt.subplots(figsize=(7, 3))
            ax.bar(labels, values, color="steelblue")
            ax.set_title(f"Nutrient Breakdown — {row['food_name'].title()} ({actual_grams}g)")
            ax.set_ylabel("grams")
            st.pyplot(fig)

            # food suggestions based on what this food is low in
            st.subheader("💡 You Might Also Want to Eat")
            low_nutrients = []
            for nutrient in ["protein_g", "fiber_g", "calcium_mg", "iron_mg"]:
                if row[nutrient] * multiplier < (RDA[nutrient] * 0.1):
                    low_nutrients.append(nutrient)

            if low_nutrients:
                for nutrient in low_nutrients:
                    nice_name = nutrient.replace("_g", "").replace("_mg", "").title()
                    st.markdown(f"This food is low in **{nice_name}**. Here are some good sources:")
                    suggestions = suggest_foods_for_nutrient(nutrient, [row["food_name"]])
                    for _, s in suggestions.iterrows():
                        st.markdown(f"- **{s['food_name'].title()}** ({s['category']}) : {round(s[nutrient], 1)} per 100g")
            else:
                st.info("This food is well-rounded in most nutrients!")


# TAB 2: DAILY MEAL LOGGER
with tab2:
    st.subheader("Log Your Full Day of Meals")
    st.markdown("Enter each food on a new line. You can add grams at the end like: `banana 150`")

    meal_input = st.text_area(
        "Your meals today",
        placeholder="banana 150\nchicken breast 200\noatmeal cooked 100\ngreek yogurt 250"
    )

    if st.button("Analyze My Day"):
        lines = [line.strip() for line in meal_input.strip().split("\n") if line.strip()]

        totals    = {key: 0.0 for key in RDA}
        found     = []
        not_found = []

        for line in lines:
            parts = line.strip().split()

            # check if user typed grams at the end like "banana 150"
            if parts and parts[-1].isdigit():
                grams = int(parts[-1])
                food  = " ".join(parts[:-1]).lower()
            else:
                grams = 100  # default to 100g if no amount given
                food  = line.lower()

            multiplier = grams / 100

            # search for food in dataset
            result = df[df["food_name"] == food]
            if result.empty:
                result = df[df["food_name"].str.contains(food, na=False)]

            if result.empty:
                not_found.append(food)
                continue

            row = result.iloc[0]
            found.append(f"{row['food_name'].title()} ({grams}g)")

            # add scaled nutrition to daily totals
            for key in totals:
                totals[key] += row[key] * multiplier

        if not_found:
            st.warning(f"Not found in database: {', '.join(not_found)}")

        if found:
            st.success(f"Logged: {', '.join(found)}")

            # calculate status for each nutrient vs RDA
            rows = []
            for key, rda_val in RDA.items():
                intake  = round(totals[key], 1)
                percent = round((intake / rda_val) * 100, 1)
                if percent < 70:
                    status = "LOW"
                elif percent > 130:
                    status = "EXCESS"
                else:
                    status = "OK"
                rows.append({
                    "Nutrient"    : key,
                    "Your Intake" : intake,
                    "RDA"         : rda_val,
                    "% of RDA"    : percent,
                    "Status"      : status
                })

            st.subheader("Daily Totals vs Recommended Daily Intake")
            results_df = pd.DataFrame(rows)
            st.dataframe(results_df, use_container_width=True)

            # bar chart comparing intake vs RDA
            st.subheader("Intake vs RDA Chart")
            nutrients_plot = ["calories", "protein_g", "carbs_g", "fat_g", "fiber_g"]
            intake_vals    = [totals[n] for n in nutrients_plot]
            rda_vals       = [RDA[n]    for n in nutrients_plot]
            chart_labels   = ["Calories", "Protein", "Carbs", "Fat", "Fiber"]

            x = range(len(chart_labels))
            fig2, ax2 = plt.subplots(figsize=(9, 4))
            ax2.bar([i - 0.2 for i in x], intake_vals, 0.4, label="Your Intake", color="steelblue")
            ax2.bar([i + 0.2 for i in x], rda_vals,    0.4, label="RDA",         color="lightcoral")
            ax2.set_xticks(list(x))
            ax2.set_xticklabels(chart_labels)
            ax2.set_title("Your Daily Intake vs Recommended Daily Allowance")
            ax2.legend()
            st.pyplot(fig2)

            # personalized feedback per nutrient
            st.subheader("Personalized Feedback")
            low_nutrients_today = []

            for row in rows:
                if row["Status"] == "LOW":
                    st.warning(f"⚠️ {row['Nutrient']} is LOW ({row['% of RDA']}% of RDA). Try adding more {row['Nutrient']}-rich foods.")
                    low_nutrients_today.append(row["Nutrient"])
                elif row["Status"] == "EXCESS":
                    st.error(f"❌ {row['Nutrient']} is EXCESS ({row['% of RDA']}% of RDA). Try to reduce.")
                else:
                    st.success(f"✅ {row['Nutrient']} looks good!")

            # food suggestions for nutrients that are low today
            if low_nutrients_today:
                st.subheader("💡 Food Suggestions to Fill Your Gaps")
                already_eaten = [f.split("(")[0].strip().lower() for f in found]

                for nutrient in low_nutrients_today:
                    # only suggest for nutrients that exist as columns in the dataset
                    if nutrient not in df.columns:
                        continue
                    nice_name = nutrient.replace("_g", "").replace("_mg", "").title()
                    st.markdown(f"**Top foods to boost your {nice_name}:**")
                    suggestions = suggest_foods_for_nutrient(nutrient, already_eaten)
                    for _, s in suggestions.iterrows():
                        val = round(s[nutrient], 1)
                        st.markdown(f"- **{s['food_name'].title()}** ({s['category']}) : {val} per 100g")