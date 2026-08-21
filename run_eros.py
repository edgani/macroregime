from final_core.production_entry import run
import json
if __name__=='__main__':
    r=run();print(json.dumps(r,indent=2))
