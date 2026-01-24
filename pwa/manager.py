"""
PWA Injection module for HereCRM.
"""
import streamlit as st
import json
from pathlib import Path

def inject_pwa(
    name: str = "HereCRM",
    short_name: str = "HereCRM",
    description: str = "Advanced Text-based CRM",
    bg_color: str = "#262730",
    theme_color: str = "#ff4b4b",
    # Note: Streamlit dynamic static pathing is often '/app/static/' or just '/static/'
    icon_path_192: str = "/icon-192.png",
    icon_path_512: str = "/icon-512.png",
    sw_path: str = "/sw.js",
    manifest_path: str = "/manifest.json",
):
    """
    Injects the PWA Logic into Streamlit with Diagnostic support.
    """
    
    # 1. Ensure manifest exists on disk
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
    
    try:
        with open(manifest_file, "w") as f:
            json.dump(manifest_data, f, indent=4)
    except Exception as e:
        st.error(f"PWA: Failed to write manifest: {e}")

    # 2. Diagnostic Info (only show if explicitly requested or in Dev Mode)
    if st.session_state.get("dev_mode", False):
        with st.sidebar.expander("🛠️ PWA Diagnostic"):
            st.write(f"Manifest Path: `{manifest_path}`")
            st.write(f"SW Path: `{sw_path}`")
            st.write(f"Script Location: `{__file__}`")
            if st.button("Force Show Install Toast"):
                st.components.v1.html("""
                    <script>
                        window.parent.document.getElementById('pwa-install-toast').style.visibility = 'visible';
                    </script>
                """, height=0)

    # 3. Inject HTML/JS/CSS
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
            transition: all 0.3s ease-in-out;
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
        <span>📲 Install {short_name}</span>
        <button id="pwa-install-btn">Install</button>
        <button id="pwa-close-btn">&times;</button>
    </div>

    <script>
        console.log("PWA: Initializing...");
        
        // Service Worker Registration
        if ('serviceWorker' in navigator) {{
            window.addEventListener('load', function() {{
                console.log("PWA: Registering SW at {sw_path}");
                navigator.serviceWorker.register('{sw_path}', {{scope: '/'}})
                .then(function(reg) {{
                    console.log('PWA: SW Registered. Scope:', reg.scope);
                }}, function(err) {{
                    console.error('PWA: SW Failed:', err);
                }});
            }});
        }}

        let deferredPrompt;
        const toast = document.getElementById('pwa-install-toast');

        window.addEventListener('beforeinstallprompt', (e) => {{
            console.log("PWA: Install event fired!");
            e.preventDefault();
            deferredPrompt = e;
            toast.style.visibility = 'visible';
            toast.style.bottom = '20px';
        }});

        document.getElementById('pwa-install-btn').addEventListener('click', async () => {{
            if (deferredPrompt) {{
                deferredPrompt.prompt();
                const {{ outcome }} = await deferredPrompt.userChoice;
                console.log("PWA: Outcome:", outcome);
                deferredPrompt = null;
                toast.style.visibility = 'hidden';
            }}
        }});

        document.getElementById('pwa-close-btn').addEventListener('click', () => {{
            toast.style.visibility = 'hidden';
        }});
        
        // Heartbeat for diagnostic
        setTimeout(() => {{
             console.log("PWA: Active and waiting for browser install events.");
        }}, 2000);
    </script>
    """, unsafe_allow_html=True)
