    if 'ism_mfg' in out:
        resolved['ism_mfg'] = out['ism_mfg']; sources['ism_mfg'] = 'fred'
    elif 'ism_mfg_backup1' in out:
        resolved['ism_mfg'] = out['ism_mfg_backup1']; sources['ism_mfg'] = 'fred_napmnoi'
    elif 'ism_mfg_backup2' in out:
        resolved['ism_mfg'] = out['ism_mfg_backup2']; sources['ism_mfg'] = 'fred_napmprod'
    else:
        ism_proxy = fetch_ism_proxy()
        if ism_proxy is not None:
            resolved['ism_mfg'] = ism_proxy; sources['ism_mfg'] = 'xli_proxy'