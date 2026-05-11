import json
import os
import copy
import logging
from datetime import datetime
from typing import Dict, Optional
import streamlit as st
from conceptmap_component import conceptmap_component, parse_conceptmap
from streamlit.runtime.state import session_state
from streamlit_experimental_session import StreamlitExperimentalSession
from task_content import (
    STUDY_TITLE, STUDY_INTRODUCTION, TASK_DESCRIPTION,
    EXTRA_MATERIALS, INITIAL_CONCEPT_MAP
)
from text_to_image import render_protected_markdown
from streamlit_scroll_to_top import scroll_to_here

logger = logging.getLogger(__name__)


# Session State Initialization
def init_session_state():
    """Initialize session state with experimental session support."""
    if "contents" not in st.session_state:
        st.session_state.contents = load_contents()

    # Auto Scroll
    if 'scroll_to_top' not in st.session_state:
        st.session_state.scroll_to_top = False


    # Initialize other defaults
    defaults = {
        "experimental_session": None,
        "mode": None,
        "learner_profile": None,
        "agent_sequence": [],
        "submit_request": False,
        "followup": False,
        "roundn": 0,
        "consent_given": False,
        "consent_declined": False,
        "attention_check_failed": False,
        "profile_initialisation_started": False,
        "session_initialized": False,
        "profile_initialized": False,
        "pre_questionnaire_completed": False,
        "clt_completed": False,
        "sus_completed": False,
        "post_questionnaire_completed": False,
        "session_finalized": False,
        "tutorial_completed": False,
        "conversation_turn": 0,
        "conversation_history": {},
        "agent_msg": None,
        "show_tutorial": False,
        "olm_dashboard_pending": False,
        "olm_snapshot": None,
        "olm_metrics_by_round": {},  # metrics cached at submit time per round
        "olm_dashboard_shown_time": None,
        "round_reflection_pending": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Initialize concept map data separately to avoid corruption
    if "cmdata" not in st.session_state or not isinstance(st.session_state.cmdata, list):
        initial_map = copy.deepcopy(st.session_state.contents["initial_map"])
        st.session_state.cmdata = [initial_map]

    # Set max rounds (now 5 total: round 1 + 4 scaffolding rounds)
    if 'max_rounds' not in st.session_state:
        st.session_state.max_rounds = 4  # Round 0 (baseline) + 3 scaffolding rounds (procedural skipped)


def load_contents():
    """Load contents configuration."""
    path = os.path.join(os.path.dirname(__file__), "contents.json")
    with open(path) as f:
        return json.load(f)


def get_current_round_data(round_num):
    """Get current round data for concept map."""
    # Ensure we have enough slots in cmdata
    while len(st.session_state.cmdata) <= round_num:
        if len(st.session_state.cmdata) > 0:
            # Copy the previous round's data as starting point
            previous_map = copy.deepcopy(st.session_state.cmdata[-1])
            st.session_state.cmdata.append(previous_map)
        else:
            # First round uses initial map
            st.session_state.cmdata.append(st.session_state.contents["initial_map"])

    return st.session_state.cmdata[round_num]


def ensure_cm_slot(round_num):
    """Guarantee that cmdata[round_num] exists."""
    while len(st.session_state.cmdata) <= round_num:
        if len(st.session_state.cmdata) > 0:
            # Copy the previous round's data as starting point
            previous_map = copy.deepcopy(st.session_state.cmdata[-1])
            st.session_state.cmdata.append(previous_map)
        else:
            # First round uses initial map
            st.session_state.cmdata.append(st.session_state.contents["initial_map"])


def render_mode_selection():
    """Render mode selection page."""
    st.header(STUDY_TITLE)
    st.markdown("---")

    # Add page refresh warning at the top
    st.error("""
    🚫 **DO NOT REFRESH THE PAGE** 

    Refreshing the page will restart your session from the beginning and you will lose all progress!
    Please complete the entire experiment in one session.
    """)

    # Display the study introduction as regular text (not protected)
    st.markdown("### Study Introduction")
    st.markdown(STUDY_INTRODUCTION)

    # Display topic as regular text (not protected)
    st.info(
        "**Topic:** International market entry challenges for a German software start-up under the Adaptive Market Gatekeeping (AMG) standard.")

    # Requirements
    st.warning("""
    ✅ **Requirements:**          

    - **18+** years old
    - **DESKTOP ONLY**
    - **ENGLISH SPEAKER**
    - **40 minutes** of focused attention
    - Complete all tasks in one session (no page refreshing)
    - Use only provided materials (no external AI assistance please, we try to test out own solution)
    """)

    # Task description and resources information
    st.info("""
    📋 **Task Description & Resources:**
               
    **ENGLISH SPEAKERS ON DESKTOP ONLY!** Participate in a research study examining how AI chatbots can enhance learning during concept mapping. You will create visual concept maps about international business market entry while receiving personalized guidance from AI agents.           

    What You'll Do:
    - Complete a brief profile questionnaire (5 minutes)
    - Create and refine concept maps across 4 rounds (25 minutes)
    - Interact with AI chatbots that provide learning guidance
    - Answer short questionnaires about your experience (5 minutes)
                                    
    During the experiment, you will have continuous access to:
    - **Task Description**: The specific problem you need to solve through concept mapping
    - **Extra Materials**: Additional resources to help you understand the topic
    - **Aid and Instructions**: From round 1 on, you can interact with a chatbot that assists you in improving your map

    These resources will be available via buttons at the top of the screen throughout all rounds. The chatbot is below the concept map.
    Your task is to create and refine a concept map that represents your understanding of the problem described in these materials with the help of the chatbot.
    """)

    # Participation rewards
    st.success("""
    💰 **Compensation & Bonus**

    What You'll receive:         
    - Base Payment
    - **Performance Bonus:** Top 10% of participants receive additional financial compensation of 10%
    - Learning Experience: Gain knowledge about international business strategies
    - AI Interaction: Experience cutting-edge educational AI technology
    """)

    # Details
    st.info("""
    🔎 **Study Details**

    - Duration: Approximately 45 minutes
    - Platform: Web-based (works on desktop)
    - Data: Fully anonymized for research purposes
    - Institution: University of St. Gallen, Switzerland
    """)


    st.markdown("**Ready to begin the experiment?**")

    # Center the experimental mode button
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.subheader("🔬 Experimental Session")
        st.markdown("""
        This research study includes:
        - **AI-powered personalized learning**
        - **Learner profiling questionnaire**
        - **4 rounds of concept mapping**
        - **Data collection for research purposes**
        """)

        if st.button("Start Experimental Session", type="primary", use_container_width=True):
            st.session_state.mode = "experimental"
            st.session_state.experimental_session = StreamlitExperimentalSession()

            # Initialize system
            if st.session_state.experimental_session.initialize_system("experimental"):
                st.session_state.session_initialized = True
                st.success("✅ Experimental session initialized!")
                st.rerun()
            else:
                st.error("❌ Failed to initialize experimental session. Please check your configuration.")


def render_consent_form():
    """Render research consent form."""
    st.header("📋 Research Study Consent Form")
    st.markdown("---")

    # Consent form content
    with st.container(border=True):
        st.markdown("""
        ### Informed Consent for Research Participation

        You are being invited to participate in a research study titled **"Agentic AI for Higher Education"**. 
        This study is being conducted by **Fiona Berger** from the **University of St. Gallen, Switzerland**. 
        You were selected to participate in this study because you are an adult learner interested in educational technology.

        **Purpose of the Research:**
        The purpose of this research study is to investigate how AI-powered agents can support learning through concept mapping activities. 
        If you agree to take part in this study, you will be asked to complete an online concept mapping exercise with AI assistance, 
        followed by questionnaires about your experience. This experiment will take you approximately **30-45 minutes** to complete.

        **Benefits:**
        Apart from the paid participation, we hope that your participation in the study may contribute to 
        improving educational technology and AI-assisted learning tools for students. Therefore, the top 10 percent of participants 
        receive an financial bonus to be paid upon analysis of all results.

        **Risks and Confidentiality:**
        We believe there are no known risks associated with this research study; however, as with any online related activity 
        the risk of a breach of confidentiality is always possible. To the best of our ability your answers in this study will 
        remain confidential. We will minimize any risks by:
        - Storing all data securely with participant IDs rather than names
        - All published results will be anonymized
        - Data will be stored on secure servers and deleted after the research is complete

        **Voluntary Participation:**
        Your participation in this study is completely voluntary and you can withdraw at any time. 

        **Contact Information:**
        If you have questions about this project or experience any issues during the study, you may contact the researcher, **Fiona Berger**, via the Prolific messaging system.

        **Consent Statement:**
        By clicking "I agree" below you are indicating that you are at least 18 years old, have read and understood this 
        consent form and agree to participate in this research study. Please print a copy of this page for your records.
        """)

    st.markdown("---")

    # Consent buttons
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("❌ No, I do not agree", type="secondary", use_container_width=True):
            st.session_state.consent_declined = True
            st.rerun()

    with col3:
        if st.button("✅ Yes, I agree", type="primary", use_container_width=True):
            st.session_state.consent_given = True

            # Log consent
            if st.session_state.experimental_session and st.session_state.experimental_session.session_logger:
                st.session_state.experimental_session.session_logger.log_event(
                    event_type="consent_given",
                    metadata={
                        "timestamp": datetime.now().isoformat(),
                        "consent": True
                    }
                )

            st.rerun()

    # Show message if consent was declined
    if st.session_state.consent_declined:
        st.error("""
        ### Thank you for your interest

        You have chosen not to participate in this research study. 

        We respect your decision. If you change your mind, you can refresh the page to start again.

        Thank you for considering participation in our research.
        """)
        st.stop()


def render_attention_check_failure():
    """Render attention check failure page."""
    st.header("❌ Attention Check Failed")
    st.markdown("---")

    st.error("""
    ### Thank you for your interest

    You have failed the attention check and cannot participate in this research study.

    We require participants to carefully read and respond to all questions to ensure data quality.

    Thank you for your time and consideration.
    """)
    st.stop()


def render_profile_login():
    with st.columns([1, 10, 1])[1]:
        st.header("Welcome to the Experiment")
        st.write("To participate in this research study, please complete the profile questionnaire.")
        st.info("Your responses will help us personalize the adaption to your learning needs.")

        if st.button("Begin Profile Setup", type='primary', use_container_width=True):
            st.session_state.profile_initialisation_started = True
            st.rerun()


def render_learner_profile():
    """Render learner profile creation page."""
    profile = st.session_state.experimental_session.create_learner_profile_form()

    if profile:
        st.session_state.learner_profile = profile
        st.session_state.profile_initialized = True

        # Initialize agent sequence
        st.session_state.agent_sequence = st.session_state.experimental_session.initialize_agent_sequence()

        st.info("📋 **Experiment Structure:**")
        st.write("**Round 0:** Initial Map Creation (No agent) - Baseline")
        st.write("**Rounds 1-3:** Agent-guided mapping sessions")
        st.write("")
        st.write("You will receive guidance from AI agents across 3 rounds to help improve your concept map.")

        st.markdown("---")
        st.info("📝 Next, you'll complete a pre-knowledge questionnaire about the task materials.")

        if st.button("Continue to Pre-Knowledge Questionnaire", type="primary"):
            st.rerun()


def render_tutorial():
    """Render interactive concept mapping tutorial."""
    st.header("📚 Concept Mapping Tutorial")
    st.markdown("---")

    st.markdown("""
    Welcome! Before starting the experiment, let's learn how to create concept maps effectively.

    **What is a concept map?**
    A concept map is a visual representation of knowledge that shows relationships between concepts using nodes (concepts) and edges (relationships). This concept map is responsive. You can zoom in and out to adapt the content to your screen.
    """)

    tutorial_steps = [
        {
            "title": "Step 1: Creating Nodes (Concepts)",
            "content": """
            **How to create a node:**
            - Click anywhere on the map with your **left mouse button** 🖱️
            - Type your concept label
            - Press **Enter** or click **OK** to confirm

            **Try it:** Create a node labeled "Learning" in the practice area below.
            """,
            "demo_map": {
                "elements": [
                    {"data": {"id": "example1", "label": "Example Concept", "x": 200, "y": 100}}
                ]
            }
        },
        {
            "title": "Step 2: Creating Edges (Relationships)",
            "content": """
            **How to create an edge:**
            - Click and **hold** on a node for **1 second** 🖱️ (source node turns red 🔴)
            - Click on another node to connect them
            - Type the relationship label (e.g., "leads to", "causes", "includes")
            - Press **Enter** or click **OK** to confirm

            **Try it:** Connect two concepts with a meaningful relationship.
            """,
            "demo_map": {
                "elements": [
                    {"data": {"id": "a", "label": "Learning", "x": 150, "y": 100}},
                    {"data": {"id": "b", "label": "Understanding", "x": 350, "y": 100}},
                    {"data": {"source": "a", "target": "b", "label": "leads to"}}
                ]
            }
        },
        {
            "title": "Step 3: Editing and Deleting",
            "content": """
            **Editing:**
            - **Double-click** on any node or edge to edit its label

            **Deleting:**
            - **Right-click** on any node or edge to delete it

            **Moving:**
            - **Drag** nodes to reposition them
            - Hold **Shift** to select multiple nodes

            **Try it:** Practice editing and moving elements in the map below.
            """,
            "demo_map": {
                "elements": [
                    {"data": {"id": "concept1", "label": "Practice", "x": 200, "y": 80}},
                    {"data": {"id": "concept2", "label": "Mastery", "x": 200, "y": 180}},
                    {"data": {"source": "concept1", "target": "concept2", "label": "leads to"}}
                ]
            }
        }
    ]

    # Tutorial navigation
    if "tutorial_step" not in st.session_state:
        st.session_state.tutorial_step = 0

    current_step = tutorial_steps[st.session_state.tutorial_step]

    # Progress indicator
    progress = (st.session_state.tutorial_step + 1) / len(tutorial_steps)
    st.progress(progress, text=f"Step {st.session_state.tutorial_step + 1} of {len(tutorial_steps)}")

    # Current step content
    st.subheader(current_step["title"])
    st.markdown(current_step["content"])

    # Practice area
    st.markdown("**Practice Area:**")
    try:
        tutorial_response = conceptmap_component(
            cm_data=current_step["demo_map"]
        )
    except Exception as e:
        st.error(f"Tutorial map error: {e}")
        tutorial_response = None

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.session_state.tutorial_step > 0:
            if st.button("← Previous", type="secondary"):
                st.session_state.tutorial_step -= 1
                st.rerun()

    with col3:
        if st.session_state.tutorial_step < len(tutorial_steps) - 1:
            if st.button("Next →", type="primary"):
                st.session_state.tutorial_step += 1
                st.rerun()
        else:
            if st.button("Complete Tutorial", type="primary"):
                st.session_state.tutorial_completed = True
                st.session_state.show_tutorial = False
                st.success("🎉 Tutorial completed! You're ready to start the experiment.")
                st.session_state.scroll_to_top = True
                st.rerun()

    # Skip option
    st.markdown("---")
    if st.button("Skip Tutorial", type="secondary"):
        st.session_state.tutorial_completed = True
        st.session_state.show_tutorial = False
        st.session_state.scroll_to_top = True
        st.rerun()


def render_agent_differentiation_question():
    """Render agent differentiation question before questionnaires."""
    st.header("🤖 Agent Differentiation")
    st.markdown("---")

    st.info("""
    Before we proceed with the final questionnaires, we'd like to know about your experience with the agents.
    """)

    with st.form("agent_differentiation"):
        st.markdown("**Were you able to differentiate between the different agents that provided guidance?**")

        differentiation = st.radio(
            "Select your answer:",
            options=[
                "Yes, I could clearly tell the agents were different",
                "Somewhat - I noticed some differences but wasn't sure",
                "No, all agents seemed the same to me",
                "I'm not sure"
            ],
            index=None  # No default selection
        )

        # Optional text field for additional comments
        st.markdown("**Additional comments (optional):**")
        comments = st.text_area(
            "If you noticed differences, what made the agents seem different? If not, why do you think they seemed the same?",
            height=100,
            placeholder="Your observations about the agents..."
        )

        submitted = st.form_submit_button("Submit", type="primary")

        if submitted:
            if not differentiation:
                st.error("Please select an answer before submitting.")
                return

            # Store the response in session data
            if st.session_state.experimental_session:
                differentiation_data = {
                    "differentiation_response": differentiation,
                    "comments": comments,
                    "timestamp": datetime.now().isoformat(),
                    "participant_id": st.session_state.learner_profile.get('unique_id',
                                                                           'N/A') if st.session_state.learner_profile else 'N/A',
                    "participant_name": st.session_state.learner_profile.get('name',
                                                                             'Unknown') if st.session_state.learner_profile else 'Unknown'
                }

                # Add to session data
                st.session_state.experimental_session.session_data["agent_differentiation"] = differentiation_data

                # Log the response
                if st.session_state.experimental_session.session_logger:
                    st.session_state.experimental_session.session_logger.log_event(
                        event_type="agent_differentiation_response",
                        metadata=differentiation_data
                    )

            # Mark as completed
            st.session_state.agent_differentiation_completed = True

            st.success("✅ Thank you for your feedback!")
            st.info("📊 Proceeding to the map adaption question...")
            st.rerun()


def render_map_adaption_question():
    """Render self-assessment of concept map adaptation between rounds."""
    st.header("🗺️ Concept Map Adaptation")
    st.markdown("---")

    st.info("""We would like to know how much you think your concept map changed between the rounds.""")

    with st.form("map_adaptation"):
        adaptation = st.radio(
            "Did you adapt your concept map between the rounds?",
            options=[
                "Yes, I actively changed or expanded my map between rounds",
                "Somewhat - I made a few adjustments but mostly kept it the same",
                "No, I barely changed my map between rounds",
                "I'm not sure"
            ],
            index=None  # No default selection
        )

        comments = st.text_area(
            "Additional comments (optional):",
            height=100,
            placeholder="What kinds of changes (if any) did you make to your map?"
        )

        submitted = st.form_submit_button("Submit", type="primary")

        if submitted:
            if not adaptation:
                st.error("Please select an answer before submitting.")
                return

            # Store response
            if st.session_state.experimental_session:
                adaptation_data = {
                    "adaptation_response": adaptation,
                    "comments": comments,
                    "timestamp": datetime.now().isoformat(),
                    "participant_id": st.session_state.learner_profile.get('unique_id',
                                                                           'N/A') if st.session_state.learner_profile else 'N/A',
                    "participant_name": st.session_state.learner_profile.get('name',
                                                                             'Unknown') if st.session_state.learner_profile else 'Unknown'
                }

                st.session_state.experimental_session.session_data["map_adaptation"] = adaptation_data

                if st.session_state.experimental_session.session_logger:
                    st.session_state.experimental_session.session_logger.log_event(
                        event_type="map_adaptation_response",
                        metadata=adaptation_data
                    )
            # Mark as completed and proceed
            st.session_state.map_adaptation_completed = True

            st.success("✅ Thank you for your feedback!")
            st.info("📋 Proceeding to the learning gains questionnaire...")
            st.rerun()


def render_summary_page():
    """Render session summary page."""
    st.header("Concept Mapping Experiment")
    st.markdown("---")
    st.write("Thank You for participating in the Concept Mapping Experiment!")
    st.balloons()

    # Calculate map summary statistics
    final_nodes = 0
    final_edges = 0

    if st.session_state.experimental_session:
        final_map = st.session_state.experimental_session.session_data.get("current_concept_map", {})
        final_nodes = len(final_map.get("concepts", []))
        final_edges = len(final_map.get("relationships", []))

        # Log map summary for easy identification
        if st.session_state.experimental_session.session_logger:
            st.session_state.experimental_session.session_logger.log_event(
                event_type="map_summary",
                metadata={
                    "final_nodes": final_nodes,
                    "final_edges": final_edges,
                    "participant_id": st.session_state.learner_profile.get('unique_id',
                                                                           'N/A') if st.session_state.learner_profile else 'N/A',
                    "participant_name": st.session_state.learner_profile.get('name',
                                                                             'Unknown') if st.session_state.learner_profile else 'Unknown'
                }
            )

    # Finalize session if not already done
    if not st.session_state.session_finalized and st.session_state.experimental_session:
        with st.spinner("Finalizing session and saving data..."):
            export_info = st.session_state.experimental_session.finalize_session()
            st.session_state.session_finalized = True

            if "error" not in export_info:
                st.success("✅ Session data saved successfully!")

    st.subheader("Session Summary")

    # Get session summary
    if st.session_state.experimental_session:
        summary = st.session_state.experimental_session.get_session_summary()

        # Get unique ID from learner profile
        unique_id = st.session_state.learner_profile.get('unique_id',
                                                         'N/A') if st.session_state.learner_profile else 'N/A'

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Participant Name:** {summary.get('participant_name', 'Demo User')}")
            st.write(f"**Prolific Experiment ID:** {unique_id}")
            st.write(f"**Mode:** {summary.get('mode', 'unknown').title()}")

        with col2:
            st.write(f"**Total Rounds Completed:** {st.session_state.max_rounds}")
            if st.session_state.mode == "experimental":
                st.write("**Session Structure:**")
                st.write("- Round 0: Baseline (own map)")
                st.write("- Rounds 1-3: Agent-guided map")

    # Display concept map statistics
    st.markdown("---")
    st.subheader("📊 Concept Map Statistics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Total Nodes Created", value=final_nodes)

    with col2:
        st.metric(label="Total Edges Created", value=final_edges)

    with col3:
        if final_nodes > 0:
            connectivity = round(final_edges / final_nodes, 2)
            st.metric(label="Connectivity Ratio", value=connectivity)
        else:
            st.metric(label="Connectivity Ratio", value="N/A")

    # Thank you message
    st.markdown("---")
    st.info("""
    📊 Your responses have been recorded for research purposes.

    Thank you for your valuable contribution to our research on AI-powered learning!
    """)

    # Leading back to Prolific
    st.markdown("---")
    st.link_button("Please return to Prolific", "https://app.prolific.com/submissions/complete?cc=C1EF9RLL", type="primary")


def render_agent_name():
    """Render agent name for current round."""
    roundn = st.session_state.roundn

    # In experimental mode, hide specific agent types from participants
    if st.session_state.mode == "experimental":
        if roundn == 0:
            agent_name = "Initial Map Creation"
        else:
            agent_name = "Agent"  # Generic name for all scaffolding agents
    else:
        # In demo mode, show the actual agent type
        if st.session_state.experimental_session:
            agent_name = st.session_state.experimental_session.get_agent_name(roundn)
        else:
            agent_name = "Demo Agent"

    st.markdown(f'<div style="font-size:20px;">🧙<b> {agent_name} Follow-Up:</b></div>', unsafe_allow_html=True)


def render_header():
    """Render page header."""
    st.header("Concept Mapping Experiment")
    st.markdown("---")

    # Add resource buttons in the header
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        # Display Round 0 as "Baseline" and others as Round 1-4
        if st.session_state.roundn == 0:
            st.subheader(f"Round 0 (Baseline) / {st.session_state.max_rounds - 1}")

        else:
            st.subheader(f"Round {st.session_state.roundn}/{st.session_state.max_rounds - 1}")

    with col2:
        if st.button("📋 Task Description", type="secondary", use_container_width=True):
            render_task_dialog()

    with col3:
        if st.button("📚 Extra Materials", type="secondary", use_container_width=True):
            render_materials_dialog()

    with col4:
        if st.button("❓ Help", type="secondary", use_container_width=True):
            render_help_dialog()

    # Show mode and participant info
    if st.session_state.mode:
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.learner_profile:
                st.caption(f"Participant: {st.session_state.learner_profile['name']}")
        with col2:
            st.caption(f"Mode: {st.session_state.mode.title()}")


@st.dialog("Task Description", width='large')
def render_task_dialog():
    """Render task description dialog with copy protection."""
    st.markdown("### 📋 Task Description")
    st.caption("This content is protected and cannot be copied.")

    # Render task description as protected image with larger font
    render_protected_markdown(TASK_DESCRIPTION, width=1100, font_size=20)


@st.dialog("Extra Materials", width='large')
def render_materials_dialog():
    """Render extra materials dialog with copy protection."""
    st.markdown("### 📚 Extra Materials")
    st.caption("This content is protected and cannot be copied.")

    # Render extra materials as protected image with larger font
    render_protected_markdown(EXTRA_MATERIALS, width=1100, font_size=20)


@st.dialog("How to use a concept map creator?", width='large')
def render_help_dialog():
    """Render help dialog for concept map editor."""
    st.subheader("Modifying nodes 🔵")
    st.markdown("""
                - Click with **Left Mouse Button** 🖱️ on any place to create a new node.
                    - Write the label and press **Enter** or click on the **OK** Button to confirm changes.
                    - Press **Escape** or drag the context map to discard changes.
                - You can move holding the **Left Mouse Button** 🖱️ on a node.
                    - You can also select multiple nodes by holding the **Shift** button. Selected nodes will be highlighted with the green color 🟢. 
                    - Selected nodes can be moved together.
                - Double Click with **Left Mouse Button** 🖱️ on a node to edit it's label.
                - Click with **Right Mouse Button** 🖱️ on a node to delete it.
                """)
    st.markdown("---")
    st.subheader("Modifying edges ↗️")
    st.markdown("""
                - Click and hold the **Left Mouse Button** 🖱️ on a node for one second to begin the edge creation. The source node will be highlighted with the red color 🔴.
                    - Click with **Left Mouse Button** 🖱️ on the other node to set it as the target node.
                    - Write the label and press **Enter** or click on the **OK** Button to confirm changes.
                    - Press **Escape** or drag the context map to discard changes.
                - Double Click with **Left Mouse Button** 🖱️ on an edge to edit it's label.
                - Click with **Right Mouse Button** 🖱️ on an edge to delete it.
                """)


def render_concept_map():
    """Render concept map editor."""
    roundn = st.session_state.roundn
    contents = st.session_state.contents
    cm_label = contents["labels"]["extend" if roundn else "initial"]["header"]

    # _, middle, right = st.columns([1, 20, 1])
    # with right:
    #     if st.button(label='❓', type='secondary'):
    #         render_help_dialog()
    # with middle:
    middle = st.container()
    with middle:
        st.write(cm_label)

        # example map
        if roundn == 0:
            st.markdown(
                "Please read the Task Description and the Extra Materials carefully. Add a minimum of 3, and up to 5 of your most important concepts and their connections in this round. Here is an example to illustrate what your baseline concept map might look like, before you receive assistance")

            img_path = os.path.join(os.path.dirname(__file__), "..", "examples", "data", "examplemap.png")
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
            else:
                st.warning(f"⚠️ Example image not found at {img_path}")

        # Create a container for the concept map
        try:
            # Ensure we have valid concept map data
            if roundn < len(st.session_state.cmdata) and isinstance(st.session_state.cmdata[roundn], dict):
                cm_data = st.session_state.cmdata[roundn]
            elif roundn > 0 and len(st.session_state.cmdata) >= roundn and isinstance(st.session_state.cmdata[roundn - 1], dict):
                # Start new round from previous round's map to preserve user edits
                cm_data = st.session_state.cmdata[roundn - 1]
            else:
                cm_data = st.session_state.contents["initial_map"]

            # Debug: Check data type before passing to component
            if not isinstance(cm_data, dict):
                st.error(f"Invalid concept map data type: {type(cm_data)}")
                cm_data = st.session_state.contents["initial_map"]

            response = conceptmap_component(
                cm_data=cm_data,
                submit_request=st.session_state.submit_request
            )
        except Exception as e:
            st.error(f"Error rendering concept map: {e}")
            response = None

    return response


# ---------------------------------------------------------------------------
# OLM (Open Learner Model) condition helpers
# ---------------------------------------------------------------------------

def is_olm_condition() -> bool:
    """Return True for any OLM condition (dashboard or no-dashboard)."""
    exp = st.session_state.experimental_session
    if exp:
        return exp.session_data.get("experimental_condition") in ("OLM_dashboard", "OLM_no_dashboard")
    return False


def is_olm_dashboard_condition() -> bool:
    """Return True only when the dashboard should be shown (OLM_dashboard condition)."""
    exp = st.session_state.experimental_session
    if exp:
        return exp.session_data.get("experimental_condition") == "OLM_dashboard"
    return False


def compute_olm_metrics(roundn: int) -> dict:
    """Return cached OLM metrics for the given round.

    Metrics are stored in olm_metrics_by_round at submit time (inside handle_response),
    so they are always based on the freshly submitted component data.
    """
    by_round = st.session_state.get("olm_metrics_by_round", {})
    if roundn in by_round:
        return by_round[roundn]
    # Fallback: return zeros (should not happen if OLM condition is active)
    return {"node_count": 0, "edge_count": 0, "connectivity_ratio": 0.0, "isolated_count": 0}


def render_olm_dashboard(roundn: int) -> None:
    """Render the Open Learner Model dashboard between rounds (OLM condition only)."""
    # Log when the dashboard is first shown for this visit
    if st.session_state.get("olm_dashboard_shown_time") is None:
        shown_time = datetime.now().isoformat()
        st.session_state.olm_dashboard_shown_time = shown_time
        session = st.session_state.get("experimental_session")
        if session and session.session_logger:
            session.session_logger.log_event(
                event_type="olm_dashboard_shown",
                metadata={"round": roundn, "timestamp": shown_time}
            )

    st.subheader("Your Concept Map — Key Metrics")
    st.caption(f"Round {roundn} snapshot (as submitted)")

    m = compute_olm_metrics(roundn)
    prev = compute_olm_metrics(roundn - 1) if roundn > 0 else None

    def _delta_html(current, previous, reverse: bool = False, decimals: int = 0) -> str:
        """Return a small colored delta line, or empty string if no previous data."""
        if previous is None:
            return ""
        diff = round(current - previous, decimals) if decimals else current - previous
        fmt = f".{decimals}f" if decimals else ""
        if diff > 0:
            label = f"+{diff:{fmt}}"
            color = "#c0392b" if reverse else "#27ae60"
        elif diff < 0:
            label = f"{diff:{fmt}}"
            color = "#27ae60" if reverse else "#c0392b"
        else:
            label = "±0"
            color = "#d4a017"
        return (
            f'<p style="font-size:0.8rem; color:{color}; margin:2px 0 0 0; font-weight:600;">'
            f'<span style="font-size:1.1rem;">{label}</span> vs. previous round</p>'
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Number of Concepts",
            value=m["node_count"],
            help="The total number of concepts currently included in your concept map.",
        )
        st.markdown(_delta_html(m["node_count"], prev["node_count"] if prev else None), unsafe_allow_html=True)
    with col2:
        st.metric(
            label="Number of Connections",
            value=m["edge_count"],
            help="The total number of connections linking concepts in your map.",
        )
        st.markdown(_delta_html(m["edge_count"], prev["edge_count"] if prev else None), unsafe_allow_html=True)
    with col3:
        st.metric(
            label="Unconnected Concepts",
            value=m["isolated_count"],
            help="The number of concepts that are not connected to any other concept.",
        )
        st.markdown(_delta_html(m["isolated_count"], prev["isolated_count"] if prev else None, reverse=True), unsafe_allow_html=True)

    st.markdown("---")

    ratio = m["connectivity_ratio"]
    if ratio < 0.8:
        color = "#c0392b"
    elif ratio < 1.2:
        color = "#d4a017"
    else:
        color = "#27ae60"

    ratio_delta_html = _delta_html(
        m["connectivity_ratio"],
        prev["connectivity_ratio"] if prev else None,
        decimals=2,
    )

    _, col_ratio, _ = st.columns([1, 2, 1])
    with col_ratio:
        st.markdown(f"""
        <div style="padding: 0.5rem 0 0.75rem 0;">
            <p style="font-size:0.875rem; color:rgb(49,51,63); margin:0 0 0.25rem 0; font-weight:400;">
                Connectivity Ratio
                <span title="The ratio of connections to concepts, indicating how strongly concepts are linked."
                      style="cursor:help; color:rgb(150,150,150); font-size:0.8rem; margin-left:4px;">&#9432;</span>
            </p>
            <p style="font-size:2.25rem; font-weight:700; color:{color}; margin:0; line-height:1.2;">{ratio}</p>
            {ratio_delta_html}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    GATE_SECONDS = 15
    shown_time = st.session_state.get("olm_dashboard_shown_time")
    elapsed = (datetime.now() - datetime.fromisoformat(shown_time)).total_seconds() if shown_time else GATE_SECONDS
    remaining = max(0, GATE_SECONDS - int(elapsed))

    _, col_btn, _ = st.columns([1, 2, 1])
    with col_btn:
        # Always render one button; JS handles the visual gate so no reruns are needed
        proceed_clicked = st.button("Proceed", type="primary", use_container_width=True,
                                    key=f"olm_proceed_r{roundn}")

        if remaining > 0:
            st.components.v1.html(f"""
                <style>body{{margin:0;font-family:sans-serif;}}</style>
                <div id="gate-msg" style="margin-top:6px;padding:0.6rem 1rem;background:#eef6fb;
                     border-left:4px solid #3498db;border-radius:4px;color:#2471a3;font-size:0.85rem;">
                    Please examine your dashboard carefully.
                    You can proceed in <strong id="cnt">{remaining}</strong> second{'s' if remaining != 1 else ''}...
                </div>
                <script>
                    var r = {remaining};

                    function findBtn() {{
                        var btns = window.parent.document.querySelectorAll('button');
                        for (var i = 0; i < btns.length; i++) {{
                            if (btns[i].textContent.trim() === 'Proceed') return btns[i];
                        }}
                        return null;
                    }}

                    function applyGate(btn) {{
                        btn.style.pointerEvents = 'none';
                        btn.style.opacity = '0.45';
                        btn.style.cursor = 'not-allowed';
                    }}

                    function removeGate(btn) {{
                        btn.style.pointerEvents = '';
                        btn.style.opacity = '';
                        btn.style.cursor = '';
                    }}

                    var btn = null;
                    var attempts = 0;
                    function init() {{
                        btn = findBtn();
                        if (!btn && ++attempts < 30) {{ setTimeout(init, 100); return; }}
                        if (btn) applyGate(btn);
                        tick();
                    }}

                    function tick() {{
                        r--;
                        var el = document.getElementById('cnt');
                        var msg = document.getElementById('gate-msg');
                        if (r > 0) {{
                            if (el) el.textContent = r;
                            setTimeout(tick, 1000);
                        }} else {{
                            if (msg) msg.style.display = 'none';
                            if (btn) removeGate(btn);
                        }}
                    }}

                    init();
                </script>
            """, height=55)

        if proceed_clicked and remaining == 0:
            # Log how long the participant stayed on the dashboard
            dismissed_time = datetime.now().isoformat()
            shown_time = st.session_state.get("olm_dashboard_shown_time")
            duration_seconds = None
            if shown_time:
                duration_seconds = round(
                    (datetime.fromisoformat(dismissed_time) - datetime.fromisoformat(shown_time)).total_seconds(), 2
                )
            session = st.session_state.get("experimental_session")
            if session and session.session_logger:
                session.session_logger.log_event(
                    event_type="olm_dashboard_dismissed",
                    metadata={
                        "round": roundn,
                        "timestamp": dismissed_time,
                        "shown_time": shown_time,
                        "duration_seconds": duration_seconds
                    }
                )
            # For round 0, log completion before advancing
            if roundn == 0 and st.session_state.experimental_session:
                current_cm_data = st.session_state.cmdata[0] if len(st.session_state.cmdata) > 0 else None
                st.session_state.experimental_session.update_concept_map_evolution(0, current_cm_data)
                st.session_state.experimental_session.add_to_conversation_history(
                    0, "system", "Round 0 completed - baseline concept map created", {"final": True}
                )
            st.session_state.olm_dashboard_shown_time = None
            st.session_state.olm_dashboard_pending = False
            st.session_state.olm_snapshot = None
            st.session_state.round_reflection_pending = True
            st.rerun()


def render_round_reflection(roundn: int) -> None:
    """Render the Round Reflection page with a single mental effort item (Paas scale)."""
    st.title("Round Reflection")
    st.markdown("---")
    st.markdown("**How much mental effort did you invest in this round?**")
    st.markdown("")

    EFFORT_OPTIONS = {
        1: "1 — Very, very low mental effort",
        2: "2 — Very low mental effort",
        3: "3 — Low mental effort",
        4: "4 — Rather low mental effort",
        5: "5 — Neither low nor high mental effort",
        6: "6 — Rather high mental effort",
        7: "7 — High mental effort",
        8: "8 — Very high mental effort",
        9: "9 — Very, very high mental effort",
    }

    rating = st.radio(
        "Select your rating:",
        options=list(EFFORT_OPTIONS.keys()),
        format_func=lambda x: EFFORT_OPTIONS[x],
        index=None,
        key=f"round_reflection_r{roundn}",
    )

    st.markdown("---")
    _, col_btn, _ = st.columns([1, 2, 1])
    with col_btn:
        if st.button("Proceed to Next Round", type="primary", use_container_width=True,
                     key=f"round_reflection_submit_r{roundn}",
                     disabled=(rating is None)):
            session = st.session_state.get("experimental_session")
            if session and session.session_logger:
                session.session_logger.log_event(
                    event_type="round_reflection_completed",
                    metadata={
                        "round": roundn,
                        "mental_effort_rating": rating,
                        "scale": "Paas (1992) 9-point mental effort scale",
                        "timestamp": datetime.now().isoformat(),
                        "experimental_condition": session.session_data.get("experimental_condition", "unknown"),
                    }
                )
            st.session_state.round_reflection_pending = False
            st.session_state.followup = False
            st.session_state.agent_msg = None
            st.session_state.roundn = 1 if roundn == 0 else roundn + 1
            st.session_state.scroll_to_top = True
            st.rerun()


# ---------------------------------------------------------------------------

def render_cm_submit_button():
    """Render concept map submit button."""
    st.markdown("---")  # Add a separator

    if st.session_state.followup:
        st.success("Concept map was submitted successfully!")
        return

    # Make the submit button more prominent
    st.markdown("### Submit Your Concept Map")

    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Submit Concept Map", type='primary', use_container_width=True,
                     disabled=st.session_state.submit_request):
            st.session_state.submit_request = True
            st.rerun()


def render_followup():
    """Render agent followup interaction with multi-turn conversation support."""
    roundn = st.session_state.roundn

    # Special handling for Round 0 - show OLM dashboard (OLM_dashboard condition) or skip directly to Round 1
    if roundn == 0:
        if is_olm_dashboard_condition():
            st.session_state.olm_dashboard_pending = True
            st.rerun()
        else:
            st.success("✅ Initial concept map submitted successfully!")
            st.info("This was your baseline concept map (Round 0). Now let's proceed with agent-guided experiment.")

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Proceed to Round 1", type="primary", use_container_width=True):
                    # Log the round 0 completion with experimental session
                    if st.session_state.experimental_session:
                        current_cm_data = st.session_state.cmdata[0] if len(st.session_state.cmdata) > 0 else None
                        st.session_state.experimental_session.update_concept_map_evolution(0, current_cm_data)
                        st.session_state.experimental_session.add_to_conversation_history(
                            0, "system", "Round 0 completed - baseline concept map created", {"final": True}
                        )

                    # Show reflection before advancing to round 1
                    st.session_state.round_reflection_pending = True
                    st.rerun()
            return

    # Initialize conversation state for this round
    round_key = f"round_{roundn}_conversation"
    if round_key not in st.session_state:
        st.session_state[round_key] = []

    conversation_history = st.session_state[round_key]

    # Initialize conversation turn counter
    conversation_turn_key = f"round_{roundn}_turn"
    if conversation_turn_key not in st.session_state:
        st.session_state[conversation_turn_key] = 0

    conversation_turn = st.session_state[conversation_turn_key]

    with st.container(border=True):
        render_agent_name()

        # Show conversation history
        if conversation_history:
            st.markdown("**Conversation History:**")
            for i, exchange in enumerate(conversation_history):
                with st.expander(f"Exchange {i + 1}", expanded=(i == len(conversation_history) - 1)):
                    st.markdown(f"**🧙 Agent:** {exchange['agent_message']}")
                    st.markdown(f"**👤 You:** {exchange['user_response']}")

        # Current agent response
        with st.container(border=True):
            current_cm_data = st.session_state.cmdata[roundn] if roundn < len(st.session_state.cmdata) else None

            # Get previous user response for context
            previous_user_response = None
            if conversation_history:
                previous_user_response = conversation_history[-1]['user_response']

            # Get agent response
            if st.session_state.experimental_session:
                if not st.session_state.agent_msg:
                    st.session_state.agent_msg = st.session_state.experimental_session.get_agent_response(
                        roundn,
                        concept_map_data=current_cm_data,
                        user_response=previous_user_response,
                        conversation_turn=conversation_turn
                    )

                    # Add to conversation history in session
                    st.session_state.experimental_session.add_to_conversation_history(
                        roundn, "agent", st.session_state.agent_msg, {"conversation_turn": conversation_turn}
                    )
            else:
                # Demo mode with conversation awareness
                if conversation_turn == 0:
                    st.session_state.agent_msg = "This is a demo response. In experimental mode, you would receive personalized AI-powered response."
                else:
                    st.session_state.agent_msg = f"Thank you for your response. This is demo follow-up #{conversation_turn}. In experimental mode, this would be a contextual response based on your input."

            st.markdown(f"**Current Response:**")
            st.write(st.session_state.agent_msg)

        # User response area - use unique key based on turn
        current_response_key = f'followup_response_r{roundn}_t{conversation_turn}'
        st.text_area(
            label='Your Response',
            placeholder="Please respond to the output above",
            height=100,
            key=current_response_key
        )

        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 1])

        user_response = st.session_state.get(current_response_key, '')

        with col1:
            # Continue conversation button
            max_user_messages = 5
            can_continue = (st.session_state.experimental_session and
                            st.session_state.experimental_session.can_continue_conversation(roundn))

            if (len(user_response) > 0 and can_continue and
                    st.button("Continue Conversation", type='secondary', use_container_width=True,
                              key=f"continue_r{roundn}_t{conversation_turn}")):

                # Add current exchange to history
                conversation_history.append({
                    'agent_message': st.session_state.agent_msg,
                    'user_response': user_response,
                    'turn': conversation_turn
                })

                # Log user response
                if st.session_state.experimental_session:
                    st.session_state.experimental_session.log_user_response(
                        roundn, user_response, current_cm_data
                    )
                    st.session_state.experimental_session.add_to_conversation_history(
                        roundn, "user", user_response, {"conversation_turn": conversation_turn}
                    )

                # Increment turn counter for next iteration
                st.session_state[conversation_turn_key] += 1
                st.session_state.agent_msg = None
                st.rerun()

        with col2:
            # Finish round button
            if (len(user_response) > 0 and
                    st.button("Finish Round", type='primary', use_container_width=True,
                              key=f"finish_r{roundn}_t{conversation_turn}")):

                # Add final exchange to history
                conversation_history.append({
                    'agent_message': st.session_state.agent_msg,
                    'user_response': user_response,
                    'turn': conversation_turn
                })

                # Log final user response
                if st.session_state.experimental_session:
                    st.session_state.experimental_session.log_user_response(
                        roundn, user_response, current_cm_data
                    )
                    st.session_state.experimental_session.add_to_conversation_history(
                        roundn, "user", user_response, {"conversation_turn": conversation_turn, "final": True}
                    )

                # Update concept map evolution
                if st.session_state.experimental_session and current_cm_data:
                    st.session_state.experimental_session.update_concept_map_evolution(
                        roundn, current_cm_data
                    )

                # Reset conversation state for next round
                st.session_state[conversation_turn_key] = 0

                if is_olm_dashboard_condition():
                    # OLM_dashboard: capture snapshot now (while cmdata[roundn] is guaranteed correct)
                    # then show dashboard before advancing to next round
                    st.session_state.olm_snapshot = copy.deepcopy(st.session_state.cmdata[roundn])
                    st.session_state.olm_dashboard_pending = True
                    st.rerun()
                else:
                    # Show reflection before advancing to next round
                    st.session_state.round_reflection_pending = True
                    st.rerun()

        with col3:
            # Show conversation limits
            if st.session_state.experimental_session:
                remaining_turns = max_user_messages - conversation_turn
                if remaining_turns > 0:
                    st.caption(f"Turns remaining: {remaining_turns}")
                else:
                    st.caption("Max turns remaining")

        # Show instructions
        if conversation_turn == 0:
            st.info(
                "💡 **Tip:** You can have up to 5 exchanges with the agent in this round. Use 'Continue Conversation' for follow-up questions or 'Finish Round' when ready to proceed.")
        elif conversation_turn >= max_user_messages - 1:
            st.warning("⚠️ This is your final exchange for this round. Click 'Finish Round' to proceed.")


def capture_concept_map_data(roundn: int, concept_map_response: Dict) -> None:
    """Capture concept map data for experimental analysis with comprehensive logging."""

    # 1. Store in session state for UI persistence
    ensure_cm_slot(roundn)
    st.session_state.cmdata[roundn] = concept_map_response

    # 2. Log to experimental session for research data
    if st.session_state.experimental_session:
        st.session_state.experimental_session.update_concept_map_evolution(
            roundn, concept_map_response
        )

    # 3. Log detailed interaction data for research analysis
    if st.session_state.experimental_session and st.session_state.experimental_session.session_logger:
        # Extract element counts for research metrics
        elements = concept_map_response.get("elements", [])
        if isinstance(elements, dict):
            dict_elements = []
            dict_elements.extend(elements.get("nodes", []))
            dict_elements.extend(elements.get("edges", []))
        else:
            dict_elements = [e for e in elements if isinstance(e, dict)]

        nodes = [e for e in dict_elements if "source" not in e.get("data", {})]
        edges = [e for e in dict_elements if "source" in e.get("data", {})]

        st.session_state.experimental_session.session_logger.log_event(
            event_type="concept_map_captured",
            metadata={
                "round_number": roundn,
                "nodes_count": len(nodes),
                "edges_count": len(edges),
                "total_elements": len(dict_elements),
                "participant_id": st.session_state.learner_profile.get(
                    "unique_id") if st.session_state.learner_profile else "unknown",
                "agent_type": get_current_agent_type(roundn),
                "capture_timestamp": datetime.now().isoformat(),
                "experimental_data": {
                    "concept_map_data": concept_map_response,
                    "session_id": st.session_state.experimental_session.session_data["session_id"]
                }
            }
        )


def get_current_agent_type(roundn: int) -> Optional[str]:
    """Get the current agent type for the given round."""
    if roundn == 0:
        return None  # Round 0 has no agent

    agent_index = roundn - 1
    if (st.session_state.experimental_session and
            agent_index < len(st.session_state.experimental_session.session_data.get("agent_sequence", []))):
        return st.session_state.experimental_session.session_data["agent_sequence"][agent_index]

    return None


def ensure_round_transition_data_integrity(from_round: int, to_round: int):
    """Ensure data integrity during round transitions for experimental analysis."""

    # 1. Capture final state of current round
    if from_round < len(st.session_state.cmdata):
        current_map_data = st.session_state.cmdata[from_round]
    else:
        current_map_data = st.session_state.contents["initial_map"]

    # 2. Log round transition for research analysis
    if st.session_state.experimental_session and st.session_state.experimental_session.session_logger:
        st.session_state.experimental_session.session_logger.log_event(
            event_type="round_transition",
            metadata={
                "from_round": from_round,
                "to_round": to_round,
                "final_map_data": current_map_data,
                "transition_timestamp": datetime.now().isoformat(),
                "participant_id": st.session_state.learner_profile.get(
                    "unique_id") if st.session_state.learner_profile else "unknown",
                "experimental_session_id": st.session_state.experimental_session.session_data["session_id"]
            }
        )

    # 3. Initialize next round with proper baseline for experimental continuity
    if to_round == 1:  # Special handling for Round 0 → Round 1 (baseline → scaffolding)
        # Copy baseline map as starting point for scaffolding rounds
        ensure_cm_slot(to_round)
        st.session_state.cmdata[to_round] = copy.deepcopy(current_map_data)

        # Log baseline preservation for research analysis
        if st.session_state.experimental_session and st.session_state.experimental_session.session_logger:
            st.session_state.experimental_session.session_logger.log_event(
                event_type="baseline_map_preserved",
                metadata={
                    "baseline_round": from_round,
                    "scaffolding_round": to_round,
                    "baseline_data": current_map_data,
                    "preservation_timestamp": datetime.now().isoformat()
                }
            )


def handle_response(response):
    """Handle concept map response with cumulative logic and enhanced debugging."""
    # Always log what we receive, even if None
    logger.debug("🔍 HANDLE_RESPONSE DEBUG:")
    logger.debug(f"   Response received: {response is not None}")
    logger.debug(f"   Response type: {type(response).__name__}")
    logger.debug(f"   Followup state: {st.session_state.followup}")
    logger.debug(f"   Submit request: {st.session_state.submit_request}")

    if response is not None:
        logger.debug(f"   Response content: {str(response)[:300]}")
        if isinstance(response, dict):
            logger.debug(f"   Has elements: {'elements' in response}")
            if "elements" in response:
                logger.debug(f"   Elements count: {len(response['elements'])}")

    # --- Real-time logging of node and edge creations ---
    if response and isinstance(response, dict) and "elements" in response:
        elements = response["elements"]
        if isinstance(elements, dict):
            dict_elements = []
            dict_elements.extend(elements.get("nodes", []))
            dict_elements.extend(elements.get("edges", []))
        else:
            dict_elements = [e for e in elements if isinstance(e, dict)]
        current_nodes = {
            e["data"]["id"] for e in dict_elements if "source" not in e.get("data", {})
        }
        current_edges = {
            e["data"]["id"] for e in dict_elements if "source" in e.get("data", {})
        }

        prev_nodes = st.session_state.get("_prev_cm_nodes")
        prev_edges = st.session_state.get("_prev_cm_edges")

        if prev_nodes is None or prev_edges is None:
            # Initialize tracking on first run without logging existing elements
            st.session_state._prev_cm_nodes = current_nodes
            st.session_state._prev_cm_edges = current_edges
        else:
            new_nodes = current_nodes - prev_nodes
            new_edges = current_edges - prev_edges

            # Prepare a parsed snapshot for logging if needed
            parsed_snapshot = parse_conceptmap(response)

            for node_id in new_nodes:
                node_data = next(
                    e["data"]
                    for e in dict_elements
                    if e.get("data", {}).get("id") == node_id
                )
                logger.info(
                    f"🆕 Node created: {node_data.get('label', '')} (id: {node_id}, x: {node_data.get('x')}, y: {node_data.get('y')})"
                )
                if (
                        st.session_state.experimental_session
                        and st.session_state.experimental_session.session_logger
                ):
                    st.session_state.experimental_session.session_logger.log_event(
                        event_type="concept_map_node_created",
                        metadata={
                            "node": node_data,
                            "nodes_count": len(parsed_snapshot.get("concepts", [])),
                            "edges_count": len(parsed_snapshot.get("relationships", [])),
                            "concept_map_snapshot": parsed_snapshot,
                        },
                    )

            for edge_id in new_edges:
                edge_data = next(
                    e["data"]
                    for e in dict_elements
                    if e.get("data", {}).get("id") == edge_id
                )
                logger.info(
                    f"🆕 Edge created: {edge_data.get('source')} -> {edge_data.get('target')} "
                    f"(label: {edge_data.get('label', '')}, id: {edge_id})"
                )
                if (
                        st.session_state.experimental_session
                        and st.session_state.experimental_session.session_logger
                ):
                    st.session_state.experimental_session.session_logger.log_event(
                        event_type="concept_map_edge_created",
                        metadata={
                            "edge": edge_data,
                            "nodes_count": len(parsed_snapshot.get("concepts", [])),
                            "edges_count": len(parsed_snapshot.get("relationships", [])),
                            "concept_map_snapshot": parsed_snapshot,
                        },
                    )

            # Update tracked state
            st.session_state._prev_cm_nodes = current_nodes
            st.session_state._prev_cm_edges = current_edges

    # During agent interaction, silently keep cmdata current so post-submit edits survive the round transition
    if st.session_state.followup and isinstance(response, dict) and response.get("elements"):
        roundn = st.session_state.roundn
        ensure_cm_slot(roundn)
        st.session_state.cmdata[roundn] = response

    if st.session_state.submit_request and response and not st.session_state.followup:
        # Guard: if the component returned empty elements, the frontend hasn't fired
        # setComponentValue yet — wait for the next render cycle
        if isinstance(response, dict) and not response.get("elements"):
            logger.info("   ⏳ submit_request=True but elements empty — waiting for frontend setComponentValue")
            return

        logger.info("   ✅ Processing response...")

        # Debug: Log what we received
        if st.session_state.experimental_session and st.session_state.experimental_session.session_logger:
            st.session_state.experimental_session.session_logger.log_event(
                event_type="handle_response_debug",
                metadata={
                    "response_type": type(response).__name__,
                    "response_preview": str(response)[:300] if response else "None",
                    "has_elements": "elements" in response if isinstance(response, dict) else False,
                    "has_action_history": "action_history" in response if isinstance(response, dict) else False
                }
            )

        # Update the current round's concept map instead of appending
        roundn = st.session_state.roundn

        # Ensure we have enough slots in cmdata
        while len(st.session_state.cmdata) <= roundn:
            # For rounds after 0, copy the previous round's data as starting point
            if len(st.session_state.cmdata) > 0:
                # Copy the previous round's concept map as the base for the new round
                previous_map = copy.deepcopy(st.session_state.cmdata[-1])
                st.session_state.cmdata.append(previous_map)
            else:
                # First round uses initial map
                st.session_state.cmdata.append(st.session_state.contents["initial_map"])

        # Update the current round's concept map with the new data
        st.session_state.cmdata[roundn] = response
        logger.info(f"   📝 Stored response in cmdata[{roundn}]")

        # OLM: cache metrics immediately while response is guaranteed fresh from the component
        if is_olm_condition():
            _parsed = parse_conceptmap(response)
            _concepts = _parsed.get("concepts", [])
            _rels = _parsed.get("relationships", [])
            _connected = set()
            for _r in _rels:
                _connected.add(_r.get("source", ""))
                _connected.add(_r.get("target", ""))
            st.session_state.olm_metrics_by_round[roundn] = {
                "node_count": len(_concepts),
                "edge_count": len(_rels),
                "connectivity_ratio": round(len(_rels) / max(1, len(_concepts)), 2),
                "isolated_count": sum(1 for _c in _concepts if _c.get("id", "") not in _connected),
            }

        # Debug: Show what we're storing
        if isinstance(response, dict) and "elements" in response:
            dict_elements = [e for e in response["elements"] if isinstance(e, dict)]
            element_count = len(dict_elements)
            st.success(f"✅ Concept map data captured: {element_count} elements")

            # Show element breakdown
            nodes = [e for e in dict_elements if "source" not in e.get("data", {})]
            edges = [e for e in dict_elements if "source" in e.get("data", {})]
            st.write(f"**Elements breakdown:** {len(nodes)} nodes, {len(edges)} edges")

            # Show first few elements for verification
            if len(dict_elements) > 0:
                st.write("**Sample elements:**")
                for i, elem in enumerate(dict_elements[:3]):
                    st.write(f"  {i + 1}. {elem}")
        else:
            st.warning("⚠️ Response received but no elements found")

        # Log the concept map update for debugging
        if st.session_state.experimental_session:
            st.session_state.experimental_session.update_concept_map_evolution(roundn, response)

        st.session_state.submit_request = False
        st.session_state.followup = True
        st.rerun()
    elif st.session_state.submit_request:
        logger.warning("   ⚠️ Submit request but no response - resetting submit_request")
        st.session_state.submit_request = False
    else:
        logger.info(
            f"   ℹ️ No action taken (response: {response is not None}, submit_request: {st.session_state.submit_request}, followup: {st.session_state.followup})"
        )


def main():
    """Main application logic."""
    init_session_state()
    st.markdown('<a id="top"></a>', unsafe_allow_html=True)
    scroll_js = """
           <script>
               const topAnchor = parent.document.getElementById('top');
               if (topAnchor) {
                   topAnchor.scrollIntoView({behavior: 'smooth'});
               }
           </script>
           """

    # Mode selection
    if not st.session_state.mode:
        render_mode_selection()
        return

    # Consent form (experimental mode only, after mode selection)
    if (st.session_state.mode == "experimental" and
            st.session_state.session_initialized and
            not st.session_state.consent_given):
        render_consent_form()
        st.components.v1.html(scroll_js)
        return

    # Learner profile login page (experimental mode only, after consent)
    if (st.session_state.mode == "experimental" and
            st.session_state.session_initialized and
            st.session_state.consent_given and
            not st.session_state.profile_initialisation_started and
            not st.session_state.profile_initialized):
        render_profile_login()
        return

    # Learner profile creation (experimental mode only)
    if (st.session_state.mode == "experimental" and
            st.session_state.session_initialized and
            st.session_state.profile_initialisation_started and
            not st.session_state.profile_initialized):
        render_learner_profile()
        return

    # Pre-knowledge questionnaire (experimental mode only)
    if (st.session_state.mode == "experimental" and
            st.session_state.profile_initialized and
            not st.session_state.pre_questionnaire_completed):
        if st.session_state.experimental_session:
            st.session_state.experimental_session.render_pre_knowledge_questionnaire()
        st.components.v1.html(scroll_js)
        return

    # Attention check failure page (experimental mode only, after pre-questionnaire)
    if (st.session_state.mode == "experimental" and
            st.session_state.attention_check_failed):
        render_attention_check_failure()
        return

    # Tutorial flow (experimental mode only)
    if (st.session_state.mode == "experimental" and
            st.session_state.profile_initialized and
            st.session_state.pre_questionnaire_completed and
            st.session_state.show_tutorial):
        render_tutorial()
        st.components.v1.html(scroll_js)
        return

    # Check if tutorial is required but not completed (experimental mode)
    if (st.session_state.mode == "experimental" and
            st.session_state.profile_initialized and
            st.session_state.pre_questionnaire_completed and
            not st.session_state.tutorial_completed and
            not st.session_state.show_tutorial):
        st.session_state.show_tutorial = True
        st.rerun()

    # Main session logic
    roundn = st.session_state.roundn

    # Check if all rounds are completed and post-task questionnaires are needed
    if roundn == st.session_state.max_rounds:
        # Agent differentiation question — disabled, not relevant for current experiment
        # if (st.session_state.mode == "experimental" and
        #         not st.session_state.get('agent_differentiation_completed', False)):
        #     render_agent_differentiation_question()
        #     return

        # Map adaptation question — disabled, not relevant for current experiment
        # if (st.session_state.mode == "experimental" and
        #         st.session_state.get('agent_differentiation_completed', False) and
        #         not st.session_state.get('map_adaptation_completed', False)):
        #     render_map_adaption_question()
        #     return

        # Post-knowledge questionnaire (experimental mode only, directly after last round)
        if (st.session_state.mode == "experimental" and
             not st.session_state.get('post_questionnaire_completed', False)):
             if st.session_state.experimental_session:
                 st.session_state.experimental_session.render_post_knowledge_questionnaire()
             st.components.v1.html(scroll_js)
             return

        # CLT questionnaire (experimental mode only, after post-knowledge questionnaire)
        if (st.session_state.mode == "experimental" and
                st.session_state.get('post_questionnaire_completed', False) and
                not st.session_state.get('clt_completed', False)):
            if st.session_state.experimental_session:
                st.session_state.experimental_session.render_clt_questionnaire()
            st.components.v1.html(scroll_js)
            return

        # SUS questionnaire (experimental mode only, after CLT)
        if (st.session_state.mode == "experimental" and
                st.session_state.get('clt_completed', False) and
                not st.session_state.get('sus_completed', False)):
            if st.session_state.experimental_session:
                st.session_state.experimental_session.render_sus_questionnaire()
            st.components.v1.html(scroll_js)
            return

        # Show summary page after all questionnaires are completed (or immediately in demo mode)
        render_summary_page()
    else:
        # OLM dashboard: shown as a standalone page between rounds
        if st.session_state.get("olm_dashboard_pending", False):
            render_olm_dashboard(st.session_state.roundn)
        # Round reflection: shown after dashboard (OLM_dashboard) or directly after round (OLM_no_dashboard)
        elif st.session_state.get("round_reflection_pending", False):
            render_round_reflection(st.session_state.roundn)
        else:
            render_header()
            # Render concept map first
            response = render_concept_map()

            # Then render submit button
            render_cm_submit_button()

            handle_response(response)

            if st.session_state.followup:
                render_followup()

    if st.session_state.scroll_to_top:
        st.components.v1.html(scroll_js)
        st.session_state.scroll_to_top = False


if __name__ == "__main__":
    main()
