import streamlit as st
import os
from google import genai
from google.genai import types

# הגדרת כותרת הדף והעיצוב
st.set_page_config(page_title="סימולציית דמיון מודרך", layout="centered")

# ודא שאתה מגדיר את ה-GEMINI_API_KEY ב-Secrets של Streamlit
# ב-Streamlit Cloud מוסיפים זאת תחת Settings -> Secrets בצורה הבאה:
# GEMINI_API_KEY = "your_api_key_here"
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("שגיאה: מפתח ה-API (GEMINI_API_KEY) אינו מוגדר במערכת. אנא הגדר אותו ב-Secrets של Streamlit.")
    st.stop()

# אתחול הלקוח של גוגל באמצעות ה-SDK החדש כפי שמופיע ב-AI Studio
@st.cache_resource
def get_genai_client():
    return genai.Client(api_key=api_key)

client = get_genai_client()

# אתחול משתני ה-Session State לניהול מצב השיחה והסימולציה
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "simulation_ended" not in st.session_state:
    st.session_state.simulation_ended = False

# כותרת האפליקציה למשתמש הקצה
st.title("🧘 סימולציית דמיון מודרך להרפיה")
st.write("ברוכים הבאים למסע הדמיון המודרך. אנא עקבו אחר הנחיות המערכת.")

# הצגת היסטוריית השיחה בצורה נקייה (ללא חשיפת הפרומפט או הגדרות המערכת)
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["text"])

# פונקציה לשליחת הודעה וקבלת תגובה מהמודל
def send_message_to_gemini(user_message=None):
    # הגדרת ה-System Instructions והגדרות הריצה המדויקות מתוך ה-AI Studio
    system_instruction = (
        "You are an expert psychological simulator and relaxation guide, specializing in "
        "evidence-based guided imagery for relaxation. Maintain a calm, supportive, and safe tone. "
        "Strictly focus on relaxation. If the user asks to end the session ('מבקש לסיים' or similar), "
        "you must declare cleanly that the simulation has reached its conclusion and lock the session by "
        "printing exactly: 'הסימולציה הגיעה לסיומה. מפגש זה ננעל וכל הנתונים נמחקו מטעמי סודיות, פרטיות ובטיחות אתית.' "
        "If the user inputs an irrelevant statement or demand not related to the journey itself, "
        "respond by stating that the question is irrelevant and offer them the choice to return to the journey or prefer to end the journey."
    )
    
    # בניית היסטוריית השיחה המלאה עבור ה-API כדי לשמור על רצף
    contents = []
    for msg in st.session_state.chat_history:
        contents.append(types.Content(
            role="user" if msg["role"] == "user" else "model",
            parts=[types.Part.from_text(text=msg["text"])]
        ))
    
    # הוספת ההודעה הנוכחית של המשתמש אם קיימת
    if user_message:
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)]
        ))

    try:
        # קריאה ל-Gemini Flash כפי שמוגדר ב-Playground שלך
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # ניתן לשנות ל-gemini-3-flash-preview בהתאם לבחירה ב-Playground
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=1.0,
                thinking_config=types.ThinkingConfig(thinking_budget=1024)  # מותאם לחשיבה (Thinking level: high)
            )
        )
        return response.text
    except Exception as e:
        st.error(f"שגיאה בתקשורת עם השרת: {e}")
        return None

# הפעלת הודעת הפתיחה אוטומטית בתחילת הסשן (אם ההיסטוריה ריקה)
if len(st.session_state.chat_history) == 0:
    with st.spinner("מאתחל את מסע ההרפיה..."):
        initial_response = send_message_to_gemini()
        if initial_response:
            st.session_state.chat_history.append({"role": "model", "text": initial_response})
            st.rerun()

# ניהול ממשק הקלט בהתאם למצב הסימולציה
if st.session_state.simulation_ended:
    st.warning("הסימולציה הגיעה לסיומה המוצלח. המפגש ננעל ומאובטח.")
    if st.button("🔄 התחל מפגש סימולציה חדש לחלוטין"):
        # איפוס מלא של ה-Session State כדי לאפשר למשתמש הבא להתחיל מחדש בצורה נקייה
        st.session_state.chat_history = []
        st.session_state.simulation_ended = False
        st.rerun()
else:
    # תיבת קלט חסומה ומאובטחת למשתמש
    if user_input := st.chat_input("כתוב את תגובתך כאן..."):
        # שמירת הודעת המשתמש והצגתה
        st.session_state.chat_history.append({"role": "user", "text": user_input})
        
        with st.spinner("המודל מעבד ומגיב..."):
            model_text = send_message_to_gemini(user_message=user_input)
        
        if model_text:
            st.session_state.chat_history.append({"role": "model", "text": model_text})
            
            # בדיקה האם המודל החליט לנעול את המפגש (לפי מילות מפתח מוגדרות)
            if "ננעל" in model_text or "לסיומה" in model_text:
                st.session_state.simulation_ended = True
            
            st.rerun()
