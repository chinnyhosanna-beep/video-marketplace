import streamlit as st
from supabase import create_client

# 1. Setup the connection
# This looks into your secrets.toml file to get the passwords
try:
    supabase_url = st.secrets["supabase"]["url"]
    supabase_key = st.secrets["supabase"]["key"]

    # Create the client (The Bridge)
    supabase = create_client(supabase_url, supabase_key)

except FileNotFoundError:
    st.error("Secrets file not found! Please create .streamlit/secrets.toml")
    st.stop()
except KeyError:
    st.error("Secrets found, but keys are missing! Check your spelling.")
    st.stop()
import streamlit as st
from video_processor import process_video  # <-- Add this line
import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import time
import os
import glob
import pandas as pd
import google.generativeai as genai

# Try to import the downloader logic
try:
    import yt_dlp
except ImportError:
    st.error("⚠️ Missing Library! Please stop the app and run: pip install yt-dlp")
    st.stop()

# --- 1. SETUP CONNECTION ---
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    
    # Configure the AI
    genai.configure(api_key=st.secrets["google"]["api_key"])
    
except FileNotFoundError:
    st.error("⚠️ Secrets file not found! Did you create .streamlit/secrets.toml?")
    st.stop()
except Exception as e:
    st.error(f"⚠️ Configuration Error: {e}")
    st.stop()

supabase: Client = create_client(url, key)

# --- 2. PAGE CONFIGURATION ---
st.set_page_config(page_title="Troveo-Like Dashboard", page_icon="🎥", layout="wide")

# Initialize Session States
if 'purchased_videos' not in st.session_state:
    st.session_state.purchased_videos = []
if 'import_view' not in st.session_state:
    st.session_state.import_view = "grid"
if "user" not in st.session_state:
    st.session_state.user = None
if "ai_metadata" not in st.session_state:
    st.session_state.ai_metadata = {}

# Custom CSS
st.markdown("""
<style>
    div[data-testid="stMetric"] { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR: AUTHENTICATION ---
with st.sidebar:
    st.header("👤 Account")
    
    # If Logged In: Show Logout Button and Menu
    if st.session_state.user:
        st.success(f"Logged in as: {st.session_state.user.user.email}")
        if st.button("Log Out"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.purchased_videos = [] # Clear local purchases on logout
            st.rerun()
            
        st.divider()
        # Menu for Logged In Users
        page = st.radio("Go to", ["Marketplace", "Dashboard", "My Uploads", "Import Video"])

    # If Guest: Show Login/Signup Forms
    else:
        page = "Marketplace" # Guests are restricted to Marketplace
        st.info("🔒 Log in to upload videos.")
        
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1: # Login Form
            email_in = st.text_input("Email", key="login_email")
            pass_in = st.text_input("Password", type="password", key="login_pass")
            if st.button("Log In"):
                try:
                    user = supabase.auth.sign_in_with_password({"email": email_in, "password": pass_in})
                    st.session_state.user = user
                    
                    # --- Load Past Purchases ---
                    try:
                        current_email = user.user.email
                        data = supabase.table("purchases").select("video_id").eq("user_email", current_email).execute()
                        st.session_state.purchased_videos = [item['video_id'] for item in data.data]
                    except Exception as e:
                        print(f"Database Fetch Error: {e}")
                    
                    st.success("Welcome back!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Login Error: {e}")

        with tab2: # Sign Up Form
            new_email = st.text_input("Email", key="signup_email")
            new_pass = st.text_input("Password", type="password", key="signup_pass")
            if st.button("Create Account"):
                try:
                    user = supabase.auth.sign_up({"email": new_email, "password": new_pass})
                    st.session_state.user = user
                    st.success("Account created! Logging you in...")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Sign Up Error: {e}")

# --- 4. FETCH DATA (Global) ---
try:
    response = supabase.table("videos_inventory").select("*").execute()
    all_videos = response.data
    total_videos = len(all_videos)
except:
    all_videos = []
    total_videos = 0

# --- 5. MAIN PAGE LOGIC ---

# ==========================================
# PAGE: DASHBOARD (Protected)
# ==========================================
if page == "Dashboard":
    st.title("📊 Analytics Dashboard")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Platform Videos", total_videos)
    with col2:
        st.metric("Total Value", f"${total_videos * 50}")
    with col3:
        st.metric("Your Active Licenses", len(st.session_state.purchased_videos))
    
    st.divider()
    
    try:
        if all_videos:
            df = pd.DataFrame(all_videos)
            st.subheader("Inventory Overview")
            st.dataframe(df)
            
            if 'category' in df.columns:
                st.subheader("Category Distribution")
                st.bar_chart(df['category'].value_counts())
        else:
            st.info("No data to show yet.")
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")

# ==========================================
# PAGE: MY UPLOADS (NEW)
# ==========================================
elif page == "My Uploads":
    st.title("📂 My Uploaded Videos")
    
    if st.session_state.user:
        current_user_id = st.session_state.user.user.id
        
        # Filter videos where owner_id matches current user
        my_videos = [v for v in all_videos if v.get('owner_id') == current_user_id]
        
        if my_videos:
            st.write(f"You have uploaded **{len(my_videos)}** videos.")
            
            # Display as a table first
            st.dataframe(pd.DataFrame(my_videos))
            
            st.divider()
            
            # Display as Grid
            cols = st.columns(3)
            for index, video in enumerate(my_videos):
                file_name = video['file_name']
                public_url = supabase.storage.from_("videos").get_public_url(file_name)
                
                with cols[index % 3]:
                    with st.container(border=True):
                        st.video(public_url)
                        st.write(f"**{video.get('title', 'Untitled')}**")
                        st.caption(f"Status: Active | Price: {video.get('price')}")
                        st.button("Edit Metadata", key=f"edit_{index}") # Placeholder for future edit feature
        else:
            st.info("You haven't uploaded any videos yet. Go to 'Import Video' to start!")
            
    else:
        st.warning("Please log in to view your uploads.")

# ==========================================
# PAGE: IMPORT VIDEO (Protected)
# ==========================================
elif page == "Import Video":
    
    # --- VIEW A: THE GRID ---
    if st.session_state.import_view == "grid":
        st.title("Select a method")
        
        # Row 1
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                st.subheader("☁️ Upload Videos")
                st.caption("AI Auto-Tagging & Upload.")
                if st.button("Use AI Uploader"):
                    st.session_state.import_view = "upload_tool"
                    st.rerun()
        with c2:
            with st.container(border=True):
                st.subheader("📦 Cloud Storage")
                st.caption("Dropbox / Drive.")
                if st.button("Connect Account"):
                    st.session_state.import_view = "cloud_form"
                    st.rerun()
        with c3:
            with st.container(border=True):
                st.subheader("🔶 Upload to S3")
                st.caption("Amazon S3 Bucket.")
                if st.button("Configure S3"):
                    st.session_state.import_view = "s3_form"
                    st.rerun()

        # Row 2
        c4, c5, c6 = st.columns(3)
        with c4:
            with st.container(border=True):
                st.subheader("🚚 Ship Drives")
                st.caption("Physical Logistics.")
                if st.button("Get Shipping Label"):
                    st.session_state.import_view = "shipping_form"
                    st.rerun()
        with c5:
            with st.container(border=True):
                st.subheader("🟥 YouTube")
                st.caption("Import from URL.")
                if st.button("Import Video"):
                    st.session_state.import_view = "youtube_form"
                    st.rerun()
        with c6:
            with st.container(border=True):
                st.subheader("🔄 Migrate S3")
                st.caption("Clone existing bucket.")
                if st.button("Start Migration"):
                    st.session_state.import_view = "migrate_form"
                    st.rerun()

    # --- VIEW B: UPLOAD TOOL (UPDATED WITH OWNER_ID) ---
    elif st.session_state.import_view == "upload_tool":
        st.title("☁️ AI Smart Upload")
        if st.button("← Back to Methods"):
            st.session_state.import_view = "grid"
            st.rerun()

        uploaded_file = st.file_uploader("Drop video here to auto-generate metadata", type=['mp4', 'mov', 'mkv', 'avi'])

        if uploaded_file:
            st.info("ℹ️ Video detected. Click 'Analyze' to let AI write the title and tags.")
            
            if st.button("✨ Analyze Video with AI"):
                try:
                    with st.spinner("🤖 Uploading to Gemini & Analyzing frames..."):
                        temp_filename = f"temp_{int(time.time())}.mp4"
                        with open(temp_filename, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        video_file = genai.upload_file(path=temp_filename)

                        while video_file.state.name == "PROCESSING":
                            time.sleep(2)
                            video_file = genai.get_file(video_file.name)

                        if video_file.state.name == "FAILED":
                            st.error("AI failed to process video.")
                        else:
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            prompt = "Analyze this video. Return a JSON-like string with: Title (short/catchy), Summary (1 sentence), and Category (Nature, Tech, People, Business, or Abstract)."
                            response = model.generate_content([video_file, prompt])
                            
                            st.session_state.ai_metadata = {
                                "raw_analysis": response.text,
                                "timestamp": datetime.now()
                            }
                            st.success("Analysis Complete!")
                            os.remove(temp_filename)

                except Exception as e:
                    st.error(f"AI Error: {e}")

            with st.form("upload_form"):
                st.write("### Edit & Confirm")
                
                pre_fill_desc = ""
                if "raw_analysis" in st.session_state.ai_metadata:
                    st.info("💡 Suggestions populated from AI analysis.")
                    pre_fill_desc = st.session_state.ai_metadata["raw_analysis"]

                video_title = st.text_input("Video Title", value="New Video")
                video_category = st.selectbox("Category", ["Nature", "Tech", "People", "Business", "Abstract"])
                video_price = st.text_input("Price", value="$50")
                video_desc = st.text_area("Description / AI Analysis", value=pre_fill_desc, height=150)
                
                if st.form_submit_button("🚀 Upload to Marketplace"):
                    try:
                        file_name = f"video_{datetime.now().timestamp()}.mp4"
                        uploaded_file.seek(0)
                        file_bytes = uploaded_file.getvalue()
                        
                        supabase.storage.from_("videos").upload(file_name, file_bytes, {"content-type": uploaded_file.type})
                        
                        # --- NEW: SAVE OWNER ID ---
                        owner_id = st.session_state.user.user.id if st.session_state.user else None
                        
                        supabase.table("videos_inventory").insert({
                            "file_name": file_name,
                            "title": video_title,
                            "category": video_category,
                            "price": video_price,
                            "owner_id": owner_id  # <--- Saving who uploaded it
                        }).execute()
                        
                        st.success("✅ Upload Complete!")
                        st.session_state.ai_metadata = {} 
                    except Exception as e:
                        st.error(f"Upload Error: {e}")

    # --- VIEW C: YOUTUBE IMPORT ---
    elif st.session_state.import_view == "youtube_form":
        st.title("🟥 Import from YouTube")
        st.info("Paste a link below.")
        if st.button("← Back to Methods"):
            st.session_state.import_view = "grid"
            st.rerun()
        yt_url = st.text_input("Paste YouTube Link here")
        if st.button("Start Import"):
            if not yt_url:
                st.warning("Please paste a link first!")
            else:
                status_box = st.empty()
                status_box.write("⏳ Initializing downloader...")
                try:
                    timestamp = int(datetime.now().timestamp())
                    file_pattern = f"yt_down_{timestamp}"
                    ydl_opts = {
                        'format': 'best[height<=720]', 
                        'outtmpl': f"{file_pattern}.%(ext)s", 
                        'quiet': True, 
                        'noplaylist': True
                    }
                    video_title = "Imported Video"
                    final_filename = None
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(yt_url, download=True)
                        video_title = info.get('title', 'YouTube Import')
                    
                    found_files = glob.glob(f"{file_pattern}.*")
                    if found_files:
                        final_filename = found_files[0]
                        status_box.write(f"🚀 Uploading '{video_title}' to cloud...")
                        with open(final_filename, "rb") as f:
                            file_bytes = f.read()
                            cloud_name = f"yt_{timestamp}.mp4"
                            supabase.storage.from_("videos").upload(cloud_name, file_bytes, {"content-type": "video/mp4"})
                            
                            # --- NEW: SAVE OWNER ID FOR YOUTUBE IMPORTS ---
                            owner_id = st.session_state.user.user.id if st.session_state.user else None
                            
                            supabase.table("videos_inventory").insert({
                                "file_name": cloud_name,
                                "title": video_title,
                                "category": "Social Import",
                                "price": "$50",
                                "owner_id": owner_id # <--- Saving who imported it
                            }).execute()
                        status_box.write("🧹 Cleaning up...")
                        os.remove(final_filename)
                        status_box.success(f"✅ Success! '{video_title}' is ready in the Marketplace.")
                    else:
                        status_box.error("Error: Download finished but no file was found.")
                except Exception as e:
                    status_box.error(f"Something went wrong: {e}")

    # --- VIEW D: SHIPPING FORM ---
    elif st.session_state.import_view == "shipping_form":
        st.title("🚚 Hard Drive Logistics")
        if st.button("← Back to Methods"):
            st.session_state.import_view = "grid"
            st.rerun()
        with st.form("shipping_form"):
            contact_email = st.text_input("Contact Email")
            drive_count = st.number_input("Number of Hard Drives", min_value=1)
            address = st.text_area("Pickup Address")
            if st.form_submit_button("Submit Request"):
                try:
                    supabase.table("service_requests").insert({
                        "request_type": "Shipping",
                        "user_contact": contact_email,
                        "details": f"Drives: {drive_count} | Addr: {address}",
                        "status": "Pending"
                    }).execute()
                    st.success("Request Received!")
                except:
                     st.info("Simulation: Request received (Database table 'service_requests' missing)")

    # --- VIEW E: S3 CONFIG FORM ---
    elif st.session_state.import_view == "s3_form":
        st.title("🔶 Configure Amazon S3")
        if st.button("← Back to Methods"):
            st.session_state.import_view = "grid"
            st.rerun()
        with st.form("s3_setup"):
            bucket_name = st.text_input("S3 Bucket Name")
            region = st.selectbox("AWS Region", ["us-east-1", "eu-central-1"])
            if st.form_submit_button("Connect Bucket"):
                try:
                    supabase.table("service_requests").insert({
                        "request_type": "S3 Connection",
                        "user_contact": "Admin",
                        "details": f"Bucket: {bucket_name} | Region: {region}",
                        "status": "Pending"
                    }).execute()
                    st.success("Configuration Saved.")
                except:
                    st.info("Simulation: Config saved (Database table 'service_requests' missing)")

    # --- VIEW F: CLOUD STORAGE FORM ---
    elif st.session_state.import_view == "cloud_form":
        st.title("📦 Import from Cloud Storage")
        st.info("Paste a public shared link from Dropbox or Google Drive.")
        if st.button("← Back to Methods"):
            st.session_state.import_view = "grid"
            st.rerun()
        with st.form("cloud_setup"):
            service = st.selectbox("Service Provider", ["Google Drive", "Dropbox", "OneDrive"])
            shared_link = st.text_input("Paste Shared Folder Link")
            notes = st.text_area("Additional Notes")
            if st.form_submit_button("Submit Link"):
                try:
                    supabase.table("service_requests").insert({
                        "request_type": "Cloud Import",
                        "user_contact": "Admin",
                        "details": f"Service: {service} | Link: {shared_link}",
                        "status": "Pending Review"
                    }).execute()
                    st.success("Link Received! System will attempt to index files.")
                except:
                    st.info("Simulation: Link received (Database table 'service_requests' missing)")

    # --- VIEW G: MIGRATION FORM ---
    elif st.session_state.import_view == "migrate_form":
        st.title("🔄 Mass Data Migration")
        st.info("Request a server-to-server migration for large datasets (>1TB).")
        if st.button("← Back to Methods"):
            st.session_state.import_view = "grid"
            st.rerun()
        with st.form("migration_setup"):
            source_provider = st.text_input("Source Provider (e.g. AWS, Azure)")
            estimated_size = st.text_input("Estimated Data Size (e.g. 50TB)")
            contact_email = st.text_input("Technical Contact Email")
            if st.form_submit_button("Request Migration"):
                try:
                    supabase.table("service_requests").insert({
                        "request_type": "Migration",
                        "user_contact": contact_email,
                        "details": f"Source: {source_provider} | Size: {estimated_size}",
                        "status": "Pending Assessment"
                    }).execute()
                    st.success("Migration Request Logged. An engineer will contact you.")
                except:
                    st.info("Simulation: Request logged (Database table 'service_requests' missing)")

# ==========================================
# PAGE: MARKETPLACE (Public)
# ==========================================
elif page == "Marketplace":
    st.title("Browse Available Licenses")
    st.caption("Welcome to the public marketplace.")
    
    # Search Bar
    search_query = st.text_input("Search videos...", placeholder="Search by title or category")
    
    # Filter Logic
    display_videos = all_videos
    if search_query:
        display_videos = [v for v in all_videos if search_query.lower() in v['title'].lower()]

    if not display_videos:
        st.info("No videos found.")
    else:
        cols = st.columns(2)
        for index, video in enumerate(display_videos):
            vid_id = video.get('id', index)
            file_name = video['file_name']
            
            # Helper to safely get URL
            public_url = supabase.storage.from_("videos").get_public_url(file_name)
            
            with cols[index % 2]:
                with st.container(border=True):
                    st.video(public_url)
                    st.write(f"**{video.get('title', 'Untitled')}**")
                    st.caption(f"📂 {video.get('category', 'General')} | 🏷️ {video.get('price','$50')}")
                    
                    if vid_id in st.session_state.purchased_videos:
                        st.link_button("⬇️ Download", public_url)
                    else:
                        # --- Buy Logic ---
                        if st.session_state.user: 
                            if st.button("Buy License", key=f"btn_{vid_id}"):
                                with st.spinner("Processing payment..."):
                                    try:
                                        supabase.table("purchases").insert({
                                            "user_email": st.session_state.user.user.email,
                                            "video_id": vid_id,
                                            "price": video.get('price', '$50')
                                        }).execute()
                                        
                                        st.session_state.purchased_videos.append(vid_id)
                                        st.success("License Purchased!")
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Purchase failed: {e}")
                        else:
                            st.warning("🔒 Log in to buy")
                            st.header("Upload New Video") # <--- This creates a header on the page

# 1. The Box where users drop files
uploaded_file = st.file_uploader("Choose a video file", type=['mp4', 'mov'])

# 2. The Logic that runs when they upload
if uploaded_file is not None:
    # We only show the "Process" button if a file is uploaded
    if st.button("Step 1: Process & Watermark"):
        
        with st.spinner("Creating preview... this takes a few seconds..."):
            # This calls the "Engine" file we made earlier
            result = process_video(uploaded_file)
            
            # If the engine works, it returns a result. If it fails, it returns "error".
            if "error" in result:
                st.error(f"Ouch! Something broke: {result['error']}")
            else:
                st.success("✅ Video ready for marketplace!")
                
                # Show the data we found
                st.write("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Extracted Data:**")
                    st.json(result['metadata'])
                with col2:
                    st.write("**Watermarked Preview:**")
                    st.video(result['preview_path'])