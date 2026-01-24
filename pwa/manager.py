"""
PWA Injection module for HereCRM.
"""
import streamlit as st
import json
import os
from pathlib import Path

def inject_pwa(
    name: str = "HereCRM",
    short_name: str = "HereCRM",
    description: str = "Advanced Text-based CRM",
    bg_color: str = "#262730",
    theme_color: str = "#ff4b4b",
    icon_path_192: str = "app/static/icon-192.png",
    icon_path_512: str = "app/static/icon-512.png",
    sw_path: str = "app/static/sw.js",
    manifest_path: str = "app/static/manifest.json",
):
    """
    Injects the PWA Logic into Streamlit.
    """
    
    # 1. Ensure manifest exists on disk for Streamlit to serve
    # We look for the 'assets' folder relative to this file
    assets_dir = Path(__file__).parent / "assets"
    manifest_file = assets_dir / "manifest.json"
    
    manifest_data = {
        "name": name,
        "short_name": short_name,
        "start_url": "/",
        "display": "standalone",
        "background_color": bg_color,
        "theme_color": theme_color,
        "description": description,
        "icons": [
            {
                "src": icon_path_192,
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": icon_path_512,
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    
    with open(manifest_file, "w") as f:
        json.dump(manifest_data, f, indent=4)

    # 2. Inject HTML/JS/CSS with Debugging
    st.markdown(f"""
    <link rel="manifest" href="{manifest_path}">
    <style>
        #pwa-install-toast {{
            visibility: hidden;
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #262730;
            color: white;
            padding: 16px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            z-index: 999999;
            display: flex;
            align-items: center;
            gap: 12px;
            font-family: sans-serif;
            border: 1px solid #444;
            transition: visibility 0.3s;
        }}
        #pwa-install-btn {{
            background: {theme_color};
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }}
        #pwa-close-btn {{
            background: transparent;
            border: none;
            color: #aaa;
            cursor: pointer;
            font-size: 20px;
        }}
    </style>
    <div id="pwa-install-toast">
        <span id="pwa-msg">Install {short_name} on your phone</span>
        <button id="pwa-install-btn">Install</button>
        <button id="pwa-close-btn">&times;</button>
    </div>

    <script>
        console.log("PWA: Initializing...");
        
        // Service Worker Registration
        if ('serviceWorker' in navigator) {{
            window.addEventListener('load', function() {{
                console.log("PWA: Attempting to register SW from {sw_path}");
                navigator.serviceWorker.register('{sw_path}', {{scope: '/'}})
                .then(function(reg) {{
                    console.log('PWA: ServiceWorker registered. Scope:', reg.scope);
                }}, function(err) {{
                    console.error('PWA: ServiceWorker registration failed:', err);
                }});
            }});
        }} else {{
            console.warn("PWA: ServiceWorker not supported in this browser.");
        }}

        // Install Prompt Logic
        let deferredPrompt;
        const toast = document.getElementById('pwa-install-toast');
        const installBtn = document.getElementById('pwa-install-btn');
        const closeBtn = document.getElementById('pwa-close-btn');

        window.addEventListener('beforeinstallprompt', (e) => {{
            console.log("PWA: 'beforeinstallprompt' event fired!");
            e.preventDefault();
            deferredPrompt = e;
            toast.style.visibility = 'visible';
        }});

        installBtn.addEventListener('click', async () => {{
            if (deferredPrompt) {{
                deferredPrompt.prompt();
                const {{ outcome }} = await deferredPrompt.userChoice;
                console.log("PWA: Install choice outcome:", outcome);
                deferredPrompt = null;
                toast.style.visibility = 'hidden';
            }}
        }});

        closeBtn.addEventListener('click', () => {{
            toast.style.visibility = 'hidden';
        }});

        // Debug: Check for standalone mode
        if (window.matchMedia('(display-mode: standalone)').matches) {{
            console.log("PWA: App is running in standalone mode.");
        }}
    </script>
    """, unsafe_allow_html=True)
