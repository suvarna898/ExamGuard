import streamlit as st
import pandas as pd

st.title("ExamGuard invigilator dashboard")
st.subheader("Candidate Monitoring")
st.write("Welcome to invigilator dashboard")
st.markdown("**High Risk:**,Take Action")
st.caption("Last updated at:12-oct-2026")
st.metric("Alerts",3)

data={
    "Candidates":["Ram","jaanu","sai","sree","siri"],
    "Integrity scores":[50,60,70,90,38],
    "Risk Level":["low","Medium","High","Low","High"]

}
df=pd.DataFrame(data)
st.dataframe(df)

alerts=pd.Series([12,5,8,4,10],index=["Tab_switch","Focus_Loss","Face_Absence","Mouse_Move","Copy/Paste"])
st.bar_chart(alerts)
st.title("Slider Example")
age=st.slider("Select Your Age",min_value=18,max_value=65,value=25)
st.write("Your Age is: ",age)
st.title("Tabs Example")

tab1,tab2,tab3=st.tabs(["Dashboard","Analytics","Settings"])
with tab1:
    st.header("Dashboard")
    st.write("Welcome to Dahboard")
with tab2:
    st.header("Analytics")
    st.write("Welcome to Analytics")
with tab3:
    st.header("Settings")
    st.write("Configure Your Settings Here")

st.title("Dropdown Example")
services=st.selectbox("Choose a Service",["Authentication","Dashboard","Exam","Notifications","Payments"])
st.write("Selected Service",services)

st.title("Buttons Example")
if st.button("Submit"):
    st.success("Button Clicked Successfully")
if st.button("Shows Message"):
    st.success("Hello! Welcome to Streamlit")
if st.button("Reset"):
    st.success("Reset Button Clicked")

