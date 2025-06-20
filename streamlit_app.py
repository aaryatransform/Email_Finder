# streamlit_app.py
import streamlit as st
import requests
import re
from bs4 import BeautifulSoup
from bs4.element import Tag
import smtplib
import socket

def get_company_domain(company):
    import urllib.parse
    headers = {'User-Agent': 'Mozilla/5.0'}
    search_queries = [
        ("Google", f"https://www.google.com/search?q={urllib.parse.quote_plus(company + ' official site')}", r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"),
        ("DuckDuckGo", f"https://duckduckgo.com/html/?q={urllib.parse.quote_plus(company + ' official site')}", r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"),
        ("Wikipedia", f"https://en.wikipedia.org/w/index.php?search={urllib.parse.quote_plus(company)}", r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"),
        ("Crunchbase", f"https://www.crunchbase.com/search/organization.companies/field/organizations/organization_name/{urllib.parse.quote_plus(company)}", r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")
    ]
    blacklist = ["google", "facebook", "linkedin", "duckduckgo", "wikipedia", "crunchbase", "youtube", "twitter", "instagram", "glassdoor", "indeed"]
    for engine, url, pattern in search_queries:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all("a", href=True)
            for a in links:
                if not isinstance(a, Tag):
                    continue
                href = a.get("href")
                if not href or not isinstance(href, str):
                    continue
                # DuckDuckGo redirect fix
                if engine == "DuckDuckGo":
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif href.startswith('/l/?uddg='):
                        try:
                            url_part = href.split('uddg=')[1].split('&')[0]
                            href = urllib.parse.unquote(url_part)
                        except Exception:
                            continue
                # Wikipedia/Crunchbase: try to find the official site in the infobox
                if engine in ["Wikipedia", "Crunchbase"] and (("wikipedia.org/wiki/" in href) or ("crunchbase.com/organization/" in href)):
                    try:
                        page_resp = requests.get(href, headers=headers, timeout=10)
                        page_soup = BeautifulSoup(page_resp.text, 'html.parser')
                        # Wikipedia: look for 'official website' in infobox
                        if engine == "Wikipedia":
                            infobox = page_soup.find('table', {'class': 'infobox'})
                            if infobox and isinstance(infobox, Tag):
                                for link in infobox.find_all('a', href=True):
                                    if not isinstance(link, Tag):
                                        continue
                                    link_href = link.get('href')
                                    if not link_href or not isinstance(link_href, str):
                                        continue
                                    match = re.search(pattern, link_href)
                                    if match and all(x not in match.group(1) for x in blacklist):
                                        return match.group(1)
                        # Crunchbase: look for website field
                        if engine == "Crunchbase":
                            for link in page_soup.find_all('a', href=True):
                                if not isinstance(link, Tag):
                                    continue
                                link_href = link.get('href')
                                if not link_href or not isinstance(link_href, str):
                                    continue
                                if 'website' in link.text.lower():
                                    match = re.search(pattern, link_href)
                                    if match and all(x not in match.group(1) for x in blacklist):
                                        return match.group(1)
                    except Exception:
                        continue
                # General search result
                match = re.search(pattern, href)
                if match and all(x not in match.group(1) for x in blacklist):
                    return match.group(1)
            # NEW: Try to extract domain from visible text in search results
            for text_elem in soup.find_all(text=True):
                if not isinstance(text_elem, str):
                    continue
                match = re.search(r"www\.([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text_elem)
                if match and all(x not in match.group(1) for x in blacklist):
                    return match.group(1)
        except Exception:
            continue
    # Fallback: Try companyname.com
    fallback_domain = company.lower().replace(' ', '') + '.com'
    try:
        resp = requests.get(f"https://{fallback_domain}", headers=headers, timeout=5)
        if resp.status_code < 400:
            return fallback_domain
    except Exception:
        pass
    return None

def get_company_email_pattern(company):
    """
    Returns a list of likely email patterns for a given company based on public sources.
    This is a simple demo using a hardcoded dictionary. In production, you could scrape or use a public API.
    """
    company_patterns = {
        'google': ["{first}@{domain}", "{first}.{last}@{domain}"],
        'microsoft': ["{first}.{last}@{domain}"],
        'amazon': ["{first}{last}@{domain}"],
        'facebook': ["{first}@{domain}"],
        'apple': ["{first}.{last}@{domain}"],
        'ibm': ["{last}@{domain}"],
        'oracle': ["{first}.{last}@{domain}"],
        'dell': ["{first}_{last}@{domain}"],
        'accenture': ["{first}.{last}@{domain}"],
        'cisco': ["{first}@{domain}"],
        'adobe': ["{first}@{domain}"],
        'twitter': ["{first}@{domain}"],
        'linkedin': ["{first}-{last}@{domain}"],
        'tesla': ["{first}@{domain}"],
        'netflix': ["{first}{last}@{domain}"],
        # Add more as needed
    }
    key = company.lower().replace(' inc', '').replace(' ltd', '').replace(' llc', '').replace(' corporation', '').replace(' corp', '').replace(' co', '').replace('.', '').replace(',', '').strip()
    return company_patterns.get(key, None)

def generate_emails(first, last, domain, middle=None, company=None):
    # Try company-specific patterns first
    patterns = []
    if company:
        company_patterns = get_company_email_pattern(company)
        if company_patterns:
            for pat in company_patterns:
                patterns.append(pat.format(first=first, last=last, domain=domain))
    # Add generic patterns
    patterns += [
        f"{first}@{domain}",
        f"{last}@{domain}",
        f"{first}.{last}@{domain}",
        f"{first[0]}{last}@{domain}",
        f"{first}{last[0]}@{domain}",
        f"{first}{last}@{domain}",
        f"{first[0]}.{last}@{domain}",
        f"{first[0]}{last[0]}@{domain}",
        f"{last}.{first}@{domain}",
        f"{last}{first}@{domain}",
        f"{first[0]}_{last}@{domain}",
        f"{first}-{last}@{domain}",
        f"{first[0]}-{last}@{domain}",
        f"{first[0]}{last[0]}{last[1] if len(last)>1 else ''}@{domain}",
    ]
    if middle:
        patterns += [
            f"{first}.{middle}.{last}@{domain}",
            f"{first[0]}{middle[0]}{last}@{domain}",
            f"{first}{middle[0]}{last}@{domain}",
            f"{first[0]}.{middle[0]}.{last}@{domain}",
            f"{first[0]}{middle[0]}{last[0]}@{domain}",
        ]
    return list(dict.fromkeys(patterns))  # Remove duplicates, preserve order

def verify_email(email):
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email))

def find_linkedin(first, last, company):
    import urllib.parse
    headers = {'User-Agent': 'Mozilla/5.0'}
    queries = [
        ("Google", f"https://www.google.com/search?q={urllib.parse.quote_plus(f'{first} {last} {company} site:linkedin.com/in')}", r'https?://[\w\.]*linkedin\.com/in/[\w\-]+'),
        ("DuckDuckGo", f"https://duckduckgo.com/html/?q={urllib.parse.quote_plus(f'{first} {last} {company} site:linkedin.com/in')}", r'https?://[\w\.]*linkedin\.com/in/[\w\-]+'),
        ("Bing", f"https://www.bing.com/search?q={urllib.parse.quote_plus(f'{first} {last} {company} site:linkedin.com/in')}", r'https?://[\w\.]*linkedin\.com/in/[\w\-]+')
    ]
    for engine, url, pattern in queries:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            for link in links:
                # Only process Tag elements
                if not isinstance(link, Tag):
                    continue
                href = link.get('href')
                if not href or not isinstance(href, str):
                    continue
                # DuckDuckGo redirect fix
                if engine == "DuckDuckGo":
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif href.startswith('/l/?uddg='):
                        try:
                            url_part = href.split('uddg=')[1].split('&')[0]
                            href = urllib.parse.unquote(url_part)
                        except Exception:
                            continue
                match = re.search(pattern, href)
                if match:
                    # Try to extract snippet/job title if available
                    snippet = link.text.strip()
                    return match.group(), snippet
        except Exception:
            continue
    return None, None

def smtp_check_email(email, timeout=10):
    """
    Attempts to verify if an email exists using SMTP 'ping'.
    Returns True if the server accepts the recipient, False otherwise.
    Note: Many servers block this, so results are not always reliable.
    """
    try:
        domain = email.split('@')[1]
        # Get MX record
        import dns.resolver
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_record = str(mx_records[0]).split()[-1].rstrip('.')
        except Exception:
            return None  # Could not resolve MX
        # SMTP conversation
        server = smtplib.SMTP(timeout=timeout)
        server.set_debuglevel(0)
        server.connect(mx_record)
        server.helo(server.local_hostname)
        server.mail('test@example.com')
        code, message = server.rcpt(email)
        server.quit()
        if code == 250 or code == 251:
            return True
        else:
            return False
    except (socket.gaierror, smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, smtplib.SMTPHeloError, smtplib.SMTPRecipientsRefused, smtplib.SMTPDataError, smtplib.SMTPException, Exception):
        return None

# Streamlit UI
st.title("🔍 Find Email & LinkedIn Profile")
st.markdown("""
<style>
body, .stApp { background-color: #18191A !important; color: #E4E6EB !important; }
.big-font { font-size: 2rem !important; font-weight: 700; color: #00B4D8; }
.result-table { background: #23272F; border-radius: 12px; padding: 18px; margin-top: 16px; box-shadow: 0 2px 8px #0002; }
.copy-btn { background: #00B4D8; color: #fff; border: none; padding: 4px 12px; border-radius: 6px; cursor: pointer; margin-left: 8px; }
.stTextInput>div>div>input { background: #23272F; color: #E4E6EB; border-radius: 6px; border: 1px solid #333; }
.stButton>button { background: linear-gradient(90deg, #00B4D8 0%, #48CAE4 100%); color: #fff; border: none; border-radius: 6px; font-weight: 600; }
.stMarkdown, .stDataFrame { color: #E4E6EB !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='big-font'>Find Professional Contact Info</div>", unsafe_allow_html=True)

full_name = st.text_input("Full Name", help="Enter first and last name")
domain_input = st.text_input("Company Domain (e.g. example.com)", help="If unknown, leave blank and use company name field")
company_input = st.text_input("Company Name (optional)", help="Used for better LinkedIn search")

if st.button("Find Contact Info"):
    if not (full_name and (domain_input or company_input)):
        st.warning("Please fill out all required fields.")
    else:
        with st.spinner("Searching..."):
            name_parts = full_name.strip().split()
            if len(name_parts) < 2:
                st.error("Please enter both first and last name.")
            else:
                first = name_parts[0]
                last = name_parts[-1]
                middle = name_parts[1] if len(name_parts) > 2 else None
                domain = domain_input.strip()
                company = company_input.strip()
                emails = generate_emails(first.lower(), last.lower(), domain, middle.lower() if middle else None, company.lower() if company else None) if domain else []
                linkedin, snippet = find_linkedin(first, last, company)
                import pandas as pd
                if emails:
                    st.markdown("<div class='result-table'><b>Possible Emails</b></div>", unsafe_allow_html=True)
                    for email in emails:
                        is_valid = verify_email(email)
                        google_search_url = f"https://www.google.com/search?q=%22{email}%22"
                        st.markdown(f"""
                        <div style='display:flex;align-items:center;gap:24px;justify-content:flex-start;background:#23272F;padding:10px 16px;margin:8px 0;border-radius:8px;'>
                            <span style='font-family:monospace;font-size:1.1em;min-width:220px;'>{email}</span>
                            <span style='min-width:40px;text-align:center;'>{'✅' if is_valid else '❌'}</span>
                            <a href='{google_search_url}' target='_blank' style='color:#00B4D8;font-weight:600;min-width:60px;text-align:center;'>Open</a>
                            <button class='copy-btn' style='min-width:60px;' onclick=\"navigator.clipboard.writeText('{email}')\">Copy</button>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No emails generated. Please provide a domain.")
                st.markdown("---")
                if linkedin:
                    st.markdown(f"<div class='result-table'><b>LinkedIn:</b> <a href='{linkedin}' target='_blank' style='color:#00B4D8'>{linkedin}</a>" + (f"<br><i>{snippet}</i>" if snippet else "") + "</div>", unsafe_allow_html=True)
                else:
                    st.info("No LinkedIn profile found.")
                st.markdown("</div>", unsafe_allow_html=True)
