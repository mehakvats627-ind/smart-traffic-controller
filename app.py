from __future__ import annotations
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from traffic.simulation import TrafficSimulation, compare_controllers, APPROACHES
from traffic.fuzzy import FuzzyTrafficController
from traffic.storage import save_run, history_frame
from traffic.renderer import render

st.set_page_config(page_title="Smart Traffic Controller", page_icon="🚦", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root{--bg:#0b1114;--panel:#151d21;--edge:#2b373a;--text:#f0e7dc;--muted:#a2aaa6;--amber:#f29a4a;--green:#63d991}
.stApp{background:radial-gradient(ellipse at 75% -20%,#1c2d36 0%,#0b1114 54%);color:var(--text);font-family:'DM Sans',sans-serif}
h1,h2,h3{font-family:'Space Grotesk',sans-serif!important;letter-spacing:-.035em}
[data-testid="stSidebar"]{background:#0d1519;border-right:1px solid #253034}
[data-testid="stMetric"]{background:linear-gradient(145deg,#192328,#12191c);border:1px solid #2a373a;border-radius:15px;padding:18px 20px;box-shadow:0 12px 32px #0002}
[data-testid="stMetricValue"]{font-family:'Space Grotesk';color:#f6eee5}
div[data-testid="stVerticalBlockBorderWrapper"]{border-color:#2b373a!important;border-radius:16px;background:linear-gradient(145deg,#182125,#12191c)}
.eyebrow{color:#d8a16e;font-size:.73rem;letter-spacing:.17em;text-transform:uppercase;font-weight:700}
.stButton>button,.stDownloadButton>button{border-radius:9px;border:1px solid #72543d;background:#392b21;color:#f4d6b4;font-weight:600}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:#f29a4a;color:white}
section[data-testid="stSidebar"] .stRadio label{padding:5px 0}
</style>""",unsafe_allow_html=True)

def init_state():
    defaults={"nav":"Overview","running":False,"sim":None,"last_comparison":None,"saved_key":None,"seed":23,"scenario":"Rush hour","controller":"Fuzzy Logic","duration":600,"custom_probs":[.12,.12,.12,.12],"fixed_durations":[25,25,25,25]}
    for k,v in defaults.items(): st.session_state.setdefault(k,v)
init_state()

with st.sidebar:
    st.markdown("<div style='font:700 1.15rem Space Grotesk;color:#f1e8df;padding:14px 2px 5px'>◢ &nbsp; SMART TRAFFIC</div><div style='color:#98a29e;font-size:.82rem;margin:0 0 24px 35px'>Adaptive signal systems</div>",unsafe_allow_html=True)
    st.session_state.nav=st.radio("Navigation",["Overview","Simulation","Fuzzy Logic","Analytics","Scenarios","Reports"],label_visibility="collapsed",index=["Overview","Simulation","Fuzzy Logic","Analytics","Scenarios","Reports"].index(st.session_state.nav))
    st.markdown("<div style='position:fixed;bottom:28px;color:#87908e;font-size:.85rem'>CITY SYSTEMS<br><span style='color:#d49a61'>●</span> Control room online</div>",unsafe_allow_html=True)

scenario=st.session_state.scenario
seed=st.session_state.seed
duration=st.session_state.duration
sim=st.session_state.sim

def make_sim():
    st.session_state.sim=TrafficSimulation(st.session_state.controller,st.session_state.scenario,st.session_state.seed,st.session_state.duration,st.session_state.custom_probs,st.session_state.fixed_durations)
    st.session_state.running=False

def charts(results):
    df=pd.DataFrame([{"Controller":name,**data["metrics"]} for name,data in results.items()])
    cols=[("avg_wait","Average waiting · s"),("avg_queue","Average queue · vehicles"),("served","Vehicles served"),("max_wait","Maximum wait · s"),("avg_travel","Average travel · s"),("stops_per_vehicle","Stops per vehicle")]
    for i in range(0,len(cols),3):
        selected=cols[i:i+3]; row=st.columns(len(selected))
        for col,(key,label) in zip(row,selected):
            fig=px.bar(df,x="Controller",y=key,color="Controller",color_discrete_map={"Fixed Time":"#a986e8","Fuzzy Logic":"#5fda91"},title=label)
            fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",showlegend=False,margin=dict(l=8,r=8,t=42,b=8),height=245)
            col.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    trend=go.Figure()
    for name,data in results.items():
        values=data["queue_series"]
        stride=max(1,len(values)//120)
        trend.add_trace(go.Scatter(x=[i/60 for i in range(0,len(values),stride)],y=values[::stride],name=name,mode="lines",line=dict(color="#a986e8" if name=="Fixed Time" else "#5fda91",width=2.5)))
    trend.update_layout(template="plotly_dark",title="Queue length through the run",xaxis_title="Time · min",yaxis_title="Queued vehicles",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",height=330)
    st.plotly_chart(trend,use_container_width=True)

st.markdown("<div class='eyebrow'>URBAN MOBILITY / CONTROL SYSTEMS</div>",unsafe_allow_html=True)
head1,head2=st.columns([3,1])
head1.title("Smart Traffic Controller")
head1.caption("Fuzzy logic based adaptive traffic signal system")
head2.markdown(f"<div style='text-align:right;padding-top:22px;color:#9fe3b5'>● &nbsp;{'Simulation running' if st.session_state.running else 'System ready'}<br><span style='color:#a2aaa6'>{sim.state.seconds if sim else 0:03d}s elapsed</span></div>",unsafe_allow_html=True)

if st.session_state.nav in ("Overview","Simulation"):
    if sim is None: make_sim(); sim=st.session_state.sim
    @st.fragment(run_every=1)
    def live_intersection():
        sim=st.session_state.sim
        if st.session_state.running: sim.step(st.session_state.get("speed",1))
        metric=sim.metrics()
        k=st.columns(4)
        for c,label,value,delta in zip(k,["Vehicles served","Average waiting","Average queue","Max waiting"],[metric["served"],f'{metric["avg_wait"]:.1f} s',f'{metric["avg_queue"]:.1f} veh',f'{metric["max_wait"]:.0f} s'],["Live count","Observed","Observed","Observed"]): c.metric(label,value,delta)
        left,right=st.columns([1.8,1])
        with left:
            with st.container(border=True):
                st.subheader("Intersection simulation")
                st.image(render(sim.snapshot()),use_container_width=True)
                a,b,c,d=st.columns([1,1,1,2])
                if a.button("▶ Play" if not st.session_state.running else "Ⅱ Pause",use_container_width=True):
                    st.session_state.running=not st.session_state.running
                if b.button("Step",use_container_width=True): sim.step(st.session_state.get("speed",1))
                if c.button("Reset",use_container_width=True): make_sim()
                d.select_slider("Speed · simulated seconds per tick",[1,2,5,10],value=1,key="speed",label_visibility="collapsed")
                st.caption(f"{sim.state.phase} approach · {sim.state.transition.upper()} · {sim.state.phase_elapsed}/{sim.state.phase_green:.0f}s green")
        with right:
            with st.container(border=True):
                st.subheader("Current signal status")
                for approach in APPROACHES:
                    count=sim.queue_counts()[approach]; active=sim.state.phase==approach
                    st.markdown(f"**{approach}** &nbsp; {'🟢 GREEN' if active and sim.state.transition=='green' else '🟠 TRANSITION' if active else '🔴 RED'} &nbsp; · &nbsp; {count} waiting")
                    st.progress(min(1,count/20))
            with st.container(border=True):
                st.subheader("Fuzzy logic inputs & output")
                target=sim.state.phase; count=sim.queue_counts()[target]
                wait=max((sim.state.seconds-v.arrived for v in sim.state.vehicles if v.approach==target),default=0)
                inference=sim.fuzzy.infer(count,wait)
                st.write(f"Queue length · **{count} vehicles**")
                st.write(f"Average waiting · **{wait} seconds**")
                st.success(f"Defuzzified green · {inference['duration']:.1f} seconds")
                st.caption(f"Active inference: {inference['selected_rule']} · selected lane {target}")
    live_intersection()
    if st.session_state.nav=="Overview":
        c1,c2=st.columns([1,1])
        with c1:
            with st.container(border=True):
                st.subheader("Controller comparison")
                controller=st.radio("Active controller",["Fixed Time","Fuzzy Logic"],horizontal=True,index=0 if st.session_state.controller=="Fixed Time" else 1)
                if controller!=st.session_state.controller: st.session_state.controller=controller; make_sim()
                if st.button("Compare both controllers",type="primary"):
                    results=compare_controllers(scenario,seed,duration,st.session_state.custom_probs,st.session_state.fixed_durations)
                    st.session_state.last_comparison=results
                    key=(scenario,seed,duration,tuple(st.session_state.custom_probs),tuple(st.session_state.fixed_durations))
                    if st.session_state.saved_key!=key: save_run(scenario,seed,duration,results); st.session_state.saved_key=key
                    st.rerun()
        with c2:
            with st.container(border=True):
                st.subheader("Active scenario")
                st.write(f"**{scenario}** · seeded arrival schedule")
                st.caption(f"{duration//60} minute analysis window · seed {seed}")
                if st.button("Configure scenario →"): st.session_state.nav="Scenarios"; st.rerun()
    if st.session_state.last_comparison:
        st.subheader("Observed performance")
        charts(st.session_state.last_comparison)

elif st.session_state.nav=="Scenarios":
    st.title("Scenario configuration")
    with st.container(border=True):
        st.write("Choose a demand profile. Both controllers receive the identical seeded arrival schedule.")
        x,y,z=st.columns(3)
        new_scenario=x.selectbox("Traffic profile",["Normal traffic","Rush hour","Unequal traffic","Low traffic","Emergency vehicle","Custom traffic"],index=["Normal traffic","Rush hour","Unequal traffic","Low traffic","Emergency vehicle","Custom traffic"].index(scenario))
        new_seed=y.number_input("Arrival seed",min_value=0,max_value=999999,value=seed,step=1)
        mins=z.slider("Analysis duration · minutes",2,30,max(2,duration//60))
        custom=None
        if new_scenario=="Custom traffic":
            st.caption("Per-second arrival probability for each approach")
            custom=st.columns(4)
            custom=[c.slider(a,0.0,.6,.12,.01,key=f"custom_{a}") for a,c in zip(APPROACHES,custom)]
        st.caption("Fixed-time baseline · green seconds per phase")
        fixed_durations=[c.slider(a,10,60,value=v,key=f"fixed_{a}") for a,c,v in zip(APPROACHES,st.columns(4),st.session_state.fixed_durations)]
        if st.button("Apply scenario",type="primary"):
            st.session_state.scenario=new_scenario; st.session_state.seed=int(new_seed); st.session_state.duration=mins*60
            st.session_state.custom_probs=custom or st.session_state.custom_probs
            st.session_state.fixed_durations=fixed_durations
            make_sim(); st.session_state.last_comparison=None
            st.success("Scenario applied. Start a fresh run or compare controllers.")
        config={"scenario":new_scenario,"seed":int(new_seed),"duration_seconds":mins*60,"arrival_probability":custom or st.session_state.custom_probs,"fixed_green_seconds":fixed_durations}
        st.download_button("Export scenario JSON",json.dumps(config,indent=2),file_name="scenario.json",mime="application/json")

elif st.session_state.nav=="Fuzzy Logic":
    st.title("Fuzzy inference workspace")
    st.write("Mamdani inference · min implication · max aggregation · centroid defuzzification")
    a,b=st.columns(2)
    q=a.slider("Queue length",0,50,28); w=b.slider("Average waiting time · seconds",0,180,75)
    engine=FuzzyTrafficController(); result=engine.infer(q,w)
    c1,c2,c3=st.columns(3); c1.metric("Defuzzified green",f"{result['duration']:.1f} s"); c2.metric("Selected rule",result["selected_rule"]); c3.metric("Controller", "Adaptive Mamdani")
    p1,p2=st.columns(2)
    with p1,st.container(border=True):
        st.subheader("Membership degrees")
        st.write("Queue",result["queue_membership"]); st.write("Wait",result["wait_membership"])
    with p2,st.container(border=True):
        st.subheader("Activated fuzzy rules")
        active=[(name,val) for name,val in result["rules"] if val>0]
        st.dataframe(pd.DataFrame(active,columns=["Rule","Activation"]),hide_index=True,use_container_width=True)
    st.caption("Nine rules span all combinations of low, medium, and high demand with short, moderate, and long waits. Emergency priority and maximum-wait fairness are applied in phase selection.")

elif st.session_state.nav=="Analytics":
    st.title("Analytics & controller comparison")
    if st.session_state.last_comparison is None:
        if st.button("Run paired comparison",type="primary"):
            results=compare_controllers(scenario,seed,duration,st.session_state.custom_probs,st.session_state.fixed_durations); st.session_state.last_comparison=results
            save_run(scenario,seed,duration,results); st.rerun()
        st.info("Run a paired comparison to calculate metrics from the current scenario.")
    else: charts(st.session_state.last_comparison)
    st.caption("Both policies are evaluated on one generated arrival schedule; the same seed reproduces every arrival and vehicle type.")

elif st.session_state.nav=="Reports":
    st.title("Run history & reports")
    frame=history_frame()
    if frame.empty: st.info("No saved comparisons yet. Run a paired controller comparison from Overview or Analytics.")
    else:
        st.dataframe(frame,use_container_width=True,hide_index=True)
        st.download_button("Export history as CSV",frame.to_csv(index=False),file_name="traffic_history.csv",mime="text/csv")
        st.download_button("Export history as JSON",frame.to_json(orient="records",indent=2),file_name="traffic_history.json",mime="application/json")
