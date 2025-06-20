import streamlit as st
import requests
import re
from bs4 import BeautifulSoup
import urllib.parse
from bs4.element import Tag

# Helper Functions
def normalize_company(company):
    """Normalize company name for pattern matching."""
    return company.lower().replace(' inc', '').replace(' ltd', '').replace(' llc', '').strip()

def get_company_domain(company):
    """Find the company domain using Google search."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    query = f"https://www.google.com/search?q={urllib.parse.quote_plus(company + ' official site')}"
    try:
        response = requests.get(query, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        for link in links:
            from bs4.element import Tag
            if not isinstance(link, Tag):
                continue
            href = link.get('href')
            if not href or not isinstance(href, str):
                continue
            match = re.search(r"https?://(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", href)
            if match and not any(x in match.group(1) for x in ["google", "wikipedia", "linkedin"]):
                return match.group(1)
    except requests.RequestException:
        pass
    return None

def get_company_email_pattern(company):
    """Return specific email patterns for known companies."""
    company_patterns = {
        'google': ["{first}@{domain}", "{first}.{last}@{domain}"],
        'microsoft': ["{first}.{last}@{domain}"],
        'amazon': ["{first}{last}@{domain}"],
    }
    normalized = normalize_company(company)
    return company_patterns.get(normalized, None)

def generate_emails(first, last, domain, middle=None, company=None):
    """Generate possible email addresses based on patterns."""
    common_patterns = [
        "{first}.{last}@{domain}",
        "{first}@{domain}",
        "{first}{last}@{domain}",
        "{first_initial}{last}@{domain}",
        "{first}{last_initial}@{domain}",
        "{last}{first_initial}@{domain}",
        "{last}@{domain}",
    ]
    patterns = get_company_email_pattern(company) or common_patterns
    if middle:
        patterns += [
            "{first}.{middle}.{last}@{domain}",
            "{first}{middle_initial}{last}@{domain}",
        ]
    format_dict = {
        'first': first,
        'last': last,
        'domain': domain,
        'first_initial': first[0],
        'last_initial': last[0],
    }
    if middle:
        format_dict['middle'] = middle
        format_dict['middle_initial'] = middle[0]
    emails = [pat.format(**format_dict) for pat in patterns]
    return list(dict.fromkeys(emails))  # Remove duplicates

def verify_email(email):
    """Check if email format is valid."""
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email))

def find_linkedin(first, last, company):
    """Find LinkedIn profile using Google search."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    query = f"https://www.google.com/search?q={urllib.parse.quote_plus(f'{first} {last} {company} site:linkedin.com/in')}"
    try:
        response = requests.get(query, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            # Only process Tag elements
            if not isinstance(link, Tag):
                continue
            href = link.get('href')
            if not href or not isinstance(href, str):
                continue
            match = re.search(r'https?://[\w\.]*linkedin\.com/in/[\w\-]+', href)
            if match:
                return match.group(), link.text.strip()
    except requests.RequestException:
        pass
    return None, None

# Streamlit App
st.set_page_config(page_title="Contact Finder", page_icon="🔍")
st.title("🔍 Contact Finder")
st.markdown("Enter the full name and either the company domain or company name to find possible email addresses and LinkedIn profile.")

with st.form("contact_form"):
    full_name = st.text_input("Full Name", placeholder="e.g., John Doe", help="Enter first and last name")
    domain_input = st.text_input("Company Domain", placeholder="e.g., example.com", help="Optional if company name is provided")
    company_input = st.text_input("Company Name", placeholder="e.g., Example Inc.", help="Used for email patterns and LinkedIn search")
    submit_button = st.form_submit_button("Find Contact Info")

if submit_button:
    if not full_name or len(full_name.split()) < 2:
        st.warning("Please enter a full name with at least first and last names.")
    elif not (domain_input or company_input):
        st.warning("Please provide either a company domain or name.")
    else:
        with st.spinner("Searching..."):
            try:
                name_parts = full_name.strip().split()
                first, last = name_parts[0].lower(), name_parts[-1].lower()
                middle = name_parts[1].lower() if len(name_parts) > 2 else None
                domain = domain_input.strip().lower()
                company = company_input.strip().lower()
                
                if not domain and company:
                    domain = get_company_domain(company)
                    if domain:
                        st.info(f"Detected domain: {domain}")
                    else:
                        st.warning("Could not determine company domain.")
                
                emails = generate_emails(first, last, domain, middle, company) if domain else []
                linkedin, snippet = find_linkedin(first, last, company) if company else (None, None)
                
                if emails:
                    st.subheader("Possible Emails")
                    for email in emails:
                        is_valid = verify_email(email)
                        search_url = f"https://www.google.com/search?q=%22{email}%22"
                        status = "✅" if is_valid else "❌"
                        st.markdown(f"- {email} {status} [<a href='{search_url}' target='_blank'>Search</a>]", unsafe_allow_html=True)
                    st.caption("✅: Format valid, ❌: Invalid format")
                else:
                    st.info("No emails generated. Provide a domain or company name.")
                
                if linkedin:
                    st.subheader("LinkedIn Profile")
                    st.markdown(f"[<a href='{linkedin}' target='_blank'>{linkedin}</a>]{f'<br><i>{snippet}</i>' if snippet else ''}", unsafe_allow_html=True)
                else:
                    st.info("No LinkedIn profile found.")
                
                if emails or linkedin:
                    st.success("Search completed!")
                else:
                    st.warning("No results found. Try adjusting your inputs.")
            except Exception as e:
                st.error(f"An error occurred: {e}")