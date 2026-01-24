"""
PWA Injection module for HereCRM.
"""
import streamlit as st
import json
import urllib.parse


def inject_pwa(
    name: str = "HereCRM",
    short_name: str = "HereCRM",
    description: str = "Advanced Text-based CRM",
    bg_color: str = "#262730",
    theme_color: str = "#ff4b4b",
    icon_path_192: str = "app/static/icon-192.png",
    icon_path_512: str = "app/static/icon-512.png",
    sw_path: str = "app/static/sw.js",
):
    """
    Injects the PWA Logic (Manifest, Service Worker, Install Prompt) into a Streamlit app.
    
    This function should be called within the Streamlit app script, ideally near the top 
    of the layout but after set_page_config.
    """
    
    # 1. Build Manifest
    manifest = {
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
                "type": "image/png"
            },
            {
                "src": icon_path_512,
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }
    manifest_href = f"data:application/manifest+json,{urllib.parse.quote(json.dumps(manifest))}"

    # 2. Inject HTML/JS/CSS
    st.markdown(f"""
    <link rel="manifest" href="{manifest_href}">
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
        #pwa-install-btn:hover {{
            opacity: 0.9;
        }}
        #pwa-close-btn {{
            background: transparent;
            border: none;
            color: #aaa;
            cursor: pointer;
            font-size: 20px;
            padding: 0 4px;
        }}
        #pwa-close-btn:hover {{
            color: white;
        }}
    </style>
    <div id="pwa-install-toast">
        <span>Install {short_name} for a better experience</span>
        <button id="pwa-install-btn">Install App</button>
        <button id="pwa-close-btn">&times;</button>
    </div>

    <script>
        // Service Worker Registration
        if ('serviceWorker' in navigator) {{
            window.addEventListener('load', function() {{
                // Attempt to register with root scope. 
                // Note: This requires 'Service-Worker-Allowed: /' header if sw.js is not at root.
                navigator.serviceWorker.register('{sw_path}', {{scope: '/'}})
                .then(function(registration) {{
                    console.log('ServiceWorker registration successful with scope: ', registration.scope);
                }}, function(err) {{
                    console.log('ServiceWorker root registration failed: ', err);
                    // Fallback to default scope if root fails
                    navigator.serviceWorker.register('{sw_path}');
                }});
            }});
        }}

        // Install Prompt
        let deferredPrompt;
        const toast = document.getElementById('pwa-install-toast');
        const installBtn = document.getElementById('pwa-install-btn');
        const closeBtn = document.getElementById('pwa-close-btn');

        window.addEventListener('beforeinstallprompt', (e) => {{
            // Prevent the mini-infobar from appearing on mobile
            e.preventDefault();
            // Stash the event so it can be triggered later.
            deferredPrompt = e;
            // Update UI notify the user they can install the PWA
            toast.style.visibility = 'visible';
        }});

        installBtn.addEventListener('click', async () => {{
            if (deferredPrompt) {{
                deferredPrompt.prompt();
                const {{ outcome }} = await deferredPrompt.userChoice;
                console.log(`User response to the install prompt: ${{outcome}}`);
                deferredPrompt = null;
                toast.style.visibility = 'hidden';
            }}
        }});

        closeBtn.addEventListener('click', () => {{
            toast.style.visibility = 'hidden';
        }});
    </script>
    """, unsafe_allow_html=True)
