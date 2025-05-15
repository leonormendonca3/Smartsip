import streamlit as st
import json
from datetime import datetime, date, time as datetime_time
import pandas as pd
import os
import requests
from streamlit_lottie import st_lottie

#Defining water intake options and trophies
predefined_options = [
    {'name': 'Half cup', 'liters': 0.275, 'emoji': '🥃'},
    {'name': 'Whole cup', 'liters': 0.55, 'emoji': '🥛'},
    {'name': 'Half bottle', 'liters': 0.75, 'emoji': '🥤'},
    {'name': 'Water bottle', 'liters': 1.5, 'emoji': '🍶'},
  
]

TROPHIES = {
    "weekly": {"threshold": 7, "emoji": "🏆", "color": "blue", "name": "1 Week Champion"},
    "biweekly": {"threshold": 14, "emoji": "🎖️", "color": "green", "name": "2 Week Master"},
    "monthly": {"threshold": 30, "emoji": "🥇", "color": "orange", "name": "Monthly Hydrator"},
    "semiannual": {"threshold": 180, "emoji": "🏅", "color": "red", "name": "6 Month Legend"}
}

PROFILE_FILE = 'user_profile.json'
LOG_FILE = 'water_log.csv'
HISTORY_FILE = 'water_history.csv'

# Weather API that indicates the temperature
WEATHER_API_KEY = '4e48fa069a7a4b368f5120024253004'  
WEATHER_LOCATION = 'Lisbon,PT'


# Profile set up
def load_profile():
    try:
        with open(PROFILE_FILE, 'r') as f:
            profile = json.load(f)
            profile['wake_up_time'] = datetime.strptime(profile['wake_up_time'], "%H:%M").time()
            profile['bed_time'] = datetime.strptime(profile['bed_time'], "%H:%M").time()
            profile['physical_activity_minutes'] = profile.get('physical_activity_minutes', 0)
            profile['trophies'] = profile.get('trophies', {})
            return profile
    except Exception:
        return None

def save_profile(unit, weight, wake_up, bed_time, name="User", physical_activity_minutes=0, trophies=None):
    profile = {
        'unit': unit,
        'weight': weight,
        'wake_up_time': wake_up.strftime("%H:%M"),
        'bed_time': bed_time.strftime("%H:%M"),
        'name': name,
        'physical_activity_minutes': physical_activity_minutes,
        'trophies': trophies if trophies else {}
    }
    with open(PROFILE_FILE, 'w') as f:
        json.dump(profile, f)

def log_intake(amount, goal_unit):
    now = datetime.now()
    entry = {
        'datetime': now.strftime('%Y-%m-%d %H:%M'),
        'amount': amount,
        'unit': goal_unit
    }
    df = pd.DataFrame([entry])
    if os.path.exists(LOG_FILE):
        df.to_csv(LOG_FILE, mode='a', header=False, index=False)
    else:
        df.to_csv(LOG_FILE, mode='w', header=True, index=False)

def calculate_streaks(log_df, daily_goal):
    daily_intake = log_df.groupby(pd.Grouper(key='datetime', freq='D'))['amount'].sum()
    streaks = []
    current_streak = 0
    for date_, amount in daily_intake.items():
        if amount >= daily_goal:
            current_streak += 1
        else:
            current_streak = 0
        streaks.append((date_.date(), current_streak))
    return pd.DataFrame(streaks, columns=['date', 'streak'])

def load_log():
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE, parse_dates=['datetime'])
    else:
        return pd.DataFrame(columns=['datetime', 'amount', 'unit'])

def save_daily_history(date_, total_intake, goal_unit):
    entry = {
        'date': date_,
        'total_intake': total_intake,
        'unit': goal_unit
    }
    df = pd.DataFrame([entry])
    if os.path.exists(HISTORY_FILE):
        df.to_csv(HISTORY_FILE, mode='a', header=False, index=False)
    else:
        df.to_csv(HISTORY_FILE, mode='w', header=True, index=False)

def load_history():
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE, parse_dates=['date'])
    else:
        return pd.DataFrame(columns=['date', 'total_intake', 'unit'])

def get_current_temperature():
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={WEATHER_LOCATION}&aqi=no"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data['current']['temp_c']
        else:
            return None
    except Exception:
        return None
#Water intake formula    
def calculate_daily_goal(unit, weight, temp_c, activity_minutes):
    activity_oz = (activity_minutes // 30) * 12
    if unit == "lbs":
        base_goal = weight / 2
        temp_adjust = base_goal * 0.5 if temp_c and temp_c > 25 else 0
        activity_adjust = activity_oz
        goal_unit = "oz"
    else:
        base_goal = (weight * 2.20462 / 2) * 0.0295735
        temp_adjust = base_goal * 0.5 if temp_c and temp_c > 25 else 0
        activity_adjust = activity_oz * 0.0295735
        goal_unit = "liters"
    
    daily_goal = base_goal + temp_adjust + activity_adjust
    return daily_goal, base_goal, temp_adjust, activity_adjust, goal_unit


st.set_page_config(page_title="SmartSip", layout="wide")

st.markdown(
    "<h1 style='text-align: center; color: #1F77B4; font-size: 32px; margin-bottom: 30px;'>SmartSip Hydration Tracker</h1>",
    unsafe_allow_html=True
)

profile = load_profile()

today_str = date.today().isoformat()
if 'total_intake' not in st.session_state or st.session_state.get('last_reset_date') != today_str:
    if 'total_intake' in st.session_state and 'last_reset_date' in st.session_state:
        save_daily_history(st.session_state['last_reset_date'], st.session_state['total_intake'], profile['unit'] if profile else "liters")
    st.session_state['total_intake'] = 0.0
    st.session_state['last_reset_date'] = today_str


#Tabs available 
tab1, tab2, tab3, tab4 = st.tabs(["🚰 Log Intake", "📈 History", "⚙️ Profile", "🏆 Trophies"])

# Side bar set up
with st.sidebar:
    profile = load_profile()
    if profile is None:
        st.warning("No profile found. Please set up your profile in the Profile tab.")
    else:
        user_name = profile.get('name', 'User')
        st.header(f"👤 {user_name}, welcome back!")

        # Determine time of day and set the greeting
        current_hour = datetime.now().hour
        if current_hour < 12:
            greeting = "Good Morning, have a great start into the day, your plant waits to be watered!"
        elif 12 <= current_hour < 18:
            greeting = "Good Afternoon, let's keep track of your water drinking habits and grow a plant!"
        else:
            greeting = "Good Evening, you almost reached your goal, keep going and water your plant!"
        st.write(f"### {greeting}")

        unit = profile['unit']
        weight = profile['weight']
        wake_up = profile['wake_up_time']
        bed_time = profile['bed_time']

        # Temperature and physical activity based hydration adjustment
        current_temp = get_current_temperature()
        activity_minutes = profile.get('physical_activity_minutes', 0)

        daily_goal, base_goal, temp_adjustment, activity_adjustment, goal_unit = calculate_daily_goal(
            unit, weight, current_temp, activity_minutes
        )


        import random
# Tips Definitions, which will be randomly chosen
        tips = [
        "Drinking water can improve focus and memory.",
        "Your body is about 60% water!",
        "Drinking enough water can help prevent headaches.",
        "Water helps regulate body temperature.",
        "Staying hydrated supports healthy skin.",
        "Water flushes out toxins from your body.",
        "Hydration aids in digestion and nutrient absorption.",
        "Start your day with a glass of water to wake up your body and boost energy naturally.",
        "Feeling foggy? A sip of water can help sharpen your focus and improve concentration.",
        "Drinking water before meals can help control your appetite and support healthy weight goals.",
        "Keep your skin glowing—stay hydrated throughout the day for a fresher, healthier look.",
        "Water helps your body flush out toxins. A few extra sips can go a long way for your overall health."]
        random_tip = random.choice(tips)

        st.markdown("---")
        st.subheader("Overview")
        st.metric("💧 Daily Goal", f"{daily_goal:.2f} {goal_unit}")
        st.caption(f"Includes {activity_adjustment:.2f} {goal_unit} from {activity_minutes} min physical activity")
        st.markdown(f"Wake up time: {wake_up.strftime('%H:%M')} | Bed time: {bed_time.strftime('%H:%M')}")
        if current_temp is not None:
            st.markdown(f"🌡️ Current Temperature: **{current_temp:.1f}°C**")
            if temp_adjustment > 0:
                st.info("Temperature above 25°C - goal increased by 50%")
        else:
            st.warning("⚠️ Temperature data unavailable.")
        st.markdown("---")
        st.info(f"Tip: {random_tip} 🚰")

  
#Trophy logic definition
if profile:
    log_df = load_log()
    if not log_df.empty:
        unit = profile['unit']
        weight = profile['weight']
        current_temp = get_current_temperature()
        activity_minutes = profile.get('physical_activity_minutes', 0)

        daily_goal, base_goal, temp_adjustment, activity_adjustment, goal_unit = calculate_daily_goal(
            unit, weight, current_temp, activity_minutes
        )

        streaks_df = calculate_streaks(log_df, daily_goal)
        max_streak = streaks_df['streak'].max() if not streaks_df.empty else 0
        new_trophies = {}
        for trophy_id, criteria in TROPHIES.items():
            if max_streak >= criteria['threshold'] and not profile['trophies'].get(trophy_id):
                new_trophies[trophy_id] = datetime.now().strftime("%Y-%m-%d")
        if new_trophies:
            profile['trophies'].update(new_trophies)
            save_profile(
                profile['unit'], profile['weight'],
                profile['wake_up_time'], profile['bed_time'],
                name=profile.get('name', 'User'),
                physical_activity_minutes=profile.get('physical_activity_minutes', 0),
                trophies=profile['trophies']
            )
            st.rerun()

#Set up of the Water intake tab (tab1)
import json

def load_lottie_file(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

with tab1:
    if profile is None:
        st.warning("Please set up your profile in the Profile tab before logging intake.")
    else:
        st.subheader("Let's grow a plant today!")
        col1, col2 = st.columns([2, 3])  

        unit = profile['unit']
        weight = profile['weight']
        current_temp = get_current_temperature()
        activity_minutes = profile.get('physical_activity_minutes', 0)

        daily_goal, base_goal, temp_adjustment, activity_adjustment, goal_unit = calculate_daily_goal(
            unit, weight, current_temp, activity_minutes
        )

        with col1:
            progress = min(st.session_state['total_intake'] / daily_goal, 1.0)
            if progress < 0.34:
                lottie_path = "animations/plant_seed.json"
                stage_label = "🌱 You are currently in the **Seed** stage. Keep going!"
            elif progress < 0.67:
                lottie_path = "animations/plant_growth.json"
                stage_label = "🌿 You are currently in the **Growth** stage. Take a look at how much is remaining!"
            else:
                lottie_path = "animations/plant_flourishing.json"
                stage_label = "🪴 You are currently in the **Flourishing** stage! Well done!"

            if os.path.exists(lottie_path):
                lottie_animation = load_lottie_file(lottie_path)
                st_lottie(lottie_animation, speed=1, loop=True, height=300)
            else:
                st.error(f"Animation file not found: {lottie_path}")
            st.markdown(stage_label)

        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True) 

            option_labels = [
                f"{d['emoji']} {d['name']} ({d['liters'] / 0.0295735:.2f} oz)" if unit == 'lbs'
                else f"{d['emoji']} {d['name']} ({d['liters']:.2f} L)" for d in predefined_options
            ]
            choice = st.radio("Select the amount you drank:", option_labels + ["🔢 Custom amount"])
            if choice == "🔢 Custom amount":
                custom_amount = st.number_input(f"Enter amount in {goal_unit}:", min_value=0.0, step=0.01)
                intake_amount = custom_amount
            else:
                idx = option_labels.index(choice)
                intake_amount = predefined_options[idx]['liters']
                if unit == 'lbs':
                    intake_amount /= 0.0295735

            if st.button("Add Intake", use_container_width=True):
                st.session_state['total_intake'] += intake_amount
                log_intake(intake_amount, goal_unit)
                st.success(f"Added {intake_amount:.2f} {goal_unit} to your intake tracker!")
        
        # Display total intake and remaining
        st.markdown("---")
        st.metric("Total Intake", f"{st.session_state['total_intake']:.2f} {goal_unit}")
        st.metric("Remaining", f"{max(daily_goal - st.session_state['total_intake'], 0):.2f} {goal_unit}")
       
        progress = min(st.session_state['total_intake'] / daily_goal, 1.0)

        progress_col, percent_col = st.columns([4, 1])

        with progress_col:
            st.progress(progress, text="Hydration Goal Progress")

        with percent_col:
            st.markdown(
                f"<div style='font-size: 20px; color: #1F77B4; font-weight: bold; margin-top: 12px;'>{int(progress * 100)}%</div>",
                unsafe_allow_html=True)

if st.session_state['total_intake'] >= daily_goal and not getattr(st.session_state, 'goal_reached', False):
    st.balloons()
    st.success("🎉 Goal reached! Keep hydrating if needed.")
    st.session_state.goal_reached = True

if st.session_state['total_intake'] < daily_goal and getattr(st.session_state, 'goal_reached', False):
    st.session_state.goal_reached = False


#Set up of the History tab (tab2)
with tab2:
    if profile is None:
        st.warning("Please set up your profile in the Profile tab to view history.")
    else:
        st.subheader("Your Daily Intake History")
        log_df = load_log()
        if not log_df.empty:
            log_df['datetime'] = pd.to_datetime(log_df['datetime'])
            daily_df = log_df.groupby(pd.Grouper(key='datetime', freq='D')).agg(
                Total_Intake=('amount', 'sum'),
                unit=('unit', 'first')
            ).reset_index().rename(columns={'datetime': 'date'})
            
            st.write("Last 7 Days:")
            st.dataframe(
                daily_df.sort_values('date', ascending=False).head(7),
                use_container_width=True,
                column_config={
                    "date": "Date",
                    "Total_Intake": st.column_config.NumberColumn(
                        "Total Intake",
                        help="Daily water intake",
                        format="%.2f"
                    ),
                    "unit": "Unit"  
                }
            )
            st.line_chart(daily_df.set_index('date')['Total_Intake'], y="Total_Intake", use_container_width=True)
        else:
            st.info("No intake history yet. Start logging your drinks!")

        hist_df = load_history()
        if not hist_df.empty:
            hist_df['date'] = pd.to_datetime(hist_df['date'])
            st.line_chart(hist_df.set_index('date')['total_intake'], use_container_width=True)


# #Set up of the Profile tab (tab3)
from datetime import datetime, timedelta, time as datetime_time

with tab3:
    st.subheader("Profile Information")
    profile = load_profile()

    if profile is None:
        unit = st.radio("Weight unit", ["kg", "lbs"])
        weight = st.slider(f"Your weight ({unit})", min_value=35.0, max_value=200.0,
                           value=70.0 if unit == "kg" else 150.0, step=0.1, format="%.1f")
        wake_up = st.time_input("Wake up time", value=datetime_time(7, 0))
        bed_time = st.time_input("Bed time", value=datetime_time(23, 0))
        physical_activity = st.slider("Physical activity (minutes per day)", min_value=0, max_value=300, step=5)
        user_name = st.text_input("Enter your name", value="User")
    else:
        unit = st.radio("Weight unit", ["kg", "lbs"], index=0 if profile['unit'] == "kg" else 1)
        weight = st.slider(f"Your weight ({unit})", min_value=35.0, max_value=200.0,
                           value=float(profile['weight']), step=0.1, format="%.1f")
        wake_up = st.time_input("Wake up time", value=profile['wake_up_time'])
        bed_time = st.time_input("Bed time", value=profile['bed_time'])
        physical_activity = st.slider("Physical activity (minutes per day)", min_value=0, max_value=300, step=5,
                                      value=profile.get('physical_activity_minutes', 0))
        user_name = st.text_input("Enter your name", value=profile.get('name', 'User'))

    today = datetime.today().date()
    wake_dt = datetime.combine(today, wake_up)
    bed_dt = datetime.combine(today, bed_time)
    if bed_dt <= wake_dt:
        bed_dt += timedelta(days=1)

    sleep_duration = bed_dt - wake_dt
    sleep_hours = sleep_duration.total_seconds() / 3600
    st.caption(f"🛏️ Estimated sleep duration: {sleep_hours:.1f} hours")

    save_button = st.button("Save Profile")

    if save_button:
        if weight <= 0:
            st.error("⚠️ Weight must be greater than zero.")
        elif sleep_hours < 3 or sleep_hours > 16:
            st.error("❌ Please choose a realistic sleep time between 3 and 16 hours.")
        else:
            save_profile(unit, weight, wake_up, bed_time, name=user_name, physical_activity_minutes=physical_activity)
            st.success("Profile saved! Reloading...")
            st.rerun()

    current_temp = get_current_temperature()  
    daily_goal, base_goal, temp_adjustment, activity_adjustment, goal_unit = calculate_daily_goal(
        unit, weight, current_temp, physical_activity
    )

    st.write(f"**Estimated Daily Goal:** {daily_goal:.2f} {goal_unit}")
    st.caption(f"Includes {activity_adjustment:.2f} {goal_unit} from {physical_activity} min physical activity")


    if st.button("Reset Today's Intake"):
        st.session_state['total_intake'] = 0.0
        st.success("Today's intake reset!")

#Set up of the Trophy tab (tab4)
def show_trophies_tab(profile):
    st.subheader("🏆 Achievement Hall")
    if not profile.get('trophies'):
        st.info("No trophies earned yet. Stay hydrated to unlock achievements!")
    cols = st.columns(4)
    for idx, (trophy_id, trophy) in enumerate(TROPHIES.items()):
        with cols[idx]:
            if profile.get('trophies', {}).get(trophy_id):
                st.markdown(
                    f"<h3 style='text-align: center; color: {trophy['color']};'>{trophy['emoji']}</h3>",
                    unsafe_allow_html=True
                )
                st.success(f"**{trophy['name']}**")
                st.caption(f"Earned on {profile['trophies'][trophy_id]}")
            else:
                st.markdown(
                    f"<h3 style='text-align: center; color: gray; filter: grayscale(100%);'>{trophy['emoji']}</h3>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<p style='text-align: center; color: gray;'>{trophy['name']}</p>",
                    unsafe_allow_html=True
                )

with tab4:
    if profile is None:
        st.warning("Please set up your profile in the Profile tab to unlock and view trophies.")
    else:
        show_trophies_tab(profile)

