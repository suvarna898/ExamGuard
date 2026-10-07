from monitoring.integrity_score import (get_risk_level, calculate_integrity_score, calculate_face_presence_ratio,calculate_event_penalty)

def validate_low_risk_level_session():
    browser_events=[
        {"event_type":"tab_switch"},
        {"event_type":"focus_loss"},
    ]
    
    face_presence_ratio=98
    
    penalty = calculate_event_penalty(browser_events, face_presence_ratio)
    risk = get_risk_level(penalty)
    
    print(f"Penalty: {penalty}, Risk Level: {risk}")
    print("Expected Risk Level: low")
    print("face prensence ratio:", face_presence_ratio)
    print("penalty:", penalty)
    
def validate_medium_risk_level_session():
    browser_events=[
        {"event_type":"tab_switch"},
        {"event_type":"focus_loss"},
        {"event_type":"tab_switch"},
        {"event_type":"tab_switch"},
        {"event_type":"focus_loss"},
        {"event_type":"focus_loss"},
        {"event_type":"copy_paste"},
        {"event_type":"right_click"},
    ]
    
    face_presence_ratio=98
    
    penalty = calculate_event_penalty(browser_events, face_presence_ratio)
    risk = get_risk_level(penalty)
    
    print(f"Penalty: {penalty}, Risk Level: {risk}")
    print("Expected Risk Level: medium")
    print("face prensence ratio:", face_presence_ratio)
    print("penalty:", penalty)
    
def validate_high_risk_level_session():
    browser_events=[
        {"event_type":"tab_switch"},
        {"event_type":"tab_switch"},
        {"event_type":"focus_loss"},
        {"event_type":"tab_switch"},
        {"event_type":"tab_switch"},
        {"event_type":"focus_loss"},
        {"event_type":"focus_loss"},
        {"event_type":"copy_paste"},
        {"event_type":"right_click"},
        {"event_type":"tab_switch"},
        {"event_type":"paste_attempt"},
        {"event_type":"tab_switch"},
    ]
    
    face_presence_ratio=98
    
    penalty = calculate_event_penalty(browser_events, face_presence_ratio)
    risk = get_risk_level(penalty)
    
    print(f"Penalty: {penalty}, Risk Level: {risk}")
    print("Expected Risk Level: high")
    print("face prensence ratio:", face_presence_ratio)
    print("penalty:", penalty)
    
def main():
    validate_low_risk_level_session()
    validate_medium_risk_level_session()
    validate_high_risk_level_session()
    
if __name__ == "__main__":
    main()

# LangChain is a framework for developing applications powered by language models. It provides a standard interface for interacting with language models, as well as a set of tools and utilities for building applications that use them. LangChain is designed to be modular and extensible, allowing developers to easily add new functionality and integrate with other systems.

# How it workss?

# session exam(data) --> langchain agent -> llm model --> integrity report

# integrity_score : 85
# risk level:low
# face presence ratio: 98
# browser events:
# tab_switch : 2
# focus_loss : 1
# copy_attempt : 0
# paste_attempt : 0


# LLM will generate a readable report on our examguard session

# Session Intergrity Report:

# The session recorded an integrity score of 85 with low risk level 
# face presence ratio was maintained for approx 98% of the exam duration
# two tab switches and one focus loss event were recorded during the session.
# no copy or paste attempts were detected, indicating that the candidate maintained a high level of integrity throughout the exam. Overall, the session demonstrates a strong commitment to academic honesty and adherence to exam guidelines.


# Rules
# You are an examination integrity reporting assistant.

# Analyze the provided session evidence.

# Explain:
# 1. Integrity score
# 2. Risk level
# 3. Face presence
# 4. Browser events
# 5. Important observations

# Do not invent events.

# Do not change the calculated score.

# Do not state that suspicious activity proves misconduct.

# Use cautious, evidence-based language.