from __future__ import annotations
import sys, types

class _Cache:
    def __call__(self,*args,**kwargs):
        def deco(fn):
            fn.clear=lambda: None
            return fn
        return deco

class _Secrets(dict):
    def get(self,k,d=None): return super().get(k,d)

class FakeStreamlit(types.ModuleType):
    def __init__(self):
        super().__init__('streamlit')
        self.cache_data=_Cache()
        self.secrets=_Secrets()
        self.session_state={}
    def markdown(self,*a,**k): return None


def install_streamlit_stub():
    st=FakeStreamlit()
    sys.modules['streamlit']=st
    return st
