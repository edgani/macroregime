from run import *  # compatibility; prefer `python run.py` or Streamlit app.py
if __name__ == '__main__':
    from final_core.production_entry import run
    from final_core.build_dashboard import build_dashboard
    import json
    r=run(); d=build_dashboard(); print(json.dumps({'system_status':r.get('system_status'),'current_action':r.get('current_action'),'dashboard':str(d)},indent=2))
