"""Job Candidate Validation Engine."""

from urllib.parse import urlparse

FORBIDDEN_TITLES = {
    "facebook",
    "twitter",
    "x",
    "linkedin",
    "youtube",
    "instagram",
    "glassdoor",
    "github",
    "pinterest",
    "tiktok",
    "snapchat",
    "telegram",
    "whatsapp",
    "home",
    "about",
    "about us",
    "contact",
    "contact us",
    "sign in",
    "register",
    "login",
    "logout",
    "my profile",
    "sitemap",
    "search",
    "search jobs",
    "job search",
    "candidate experience",
    "welcome to candidate experience",
    "investors",
    "investor relations",
    "news",
    "blog",
    "press",
    "events",
    "learn more",
    "i am an employee",
    "employees",
    "explore",
    "language",
    "privacy",
    "privacy policy",
    "terms",
    "terms of use",
    "terms & conditions",
    "cookie policy",
    "copyright",
    "brand policy",
    "guest controls",
    "community guidelines",
    "accessibility",
    "user agreement",
}

FORBIDDEN_SUBSTRINGS = (
    "privacy policy",
    "terms of use",
    "cookie policy",
    "candidate experience",
    "report this post",
    "report this company",
    "followers",
    "see all employees",
    "user agreement",
    "copyright policy",
)

SOCIAL_DOMAINS = (
    "facebook.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "youtube.com",
    "instagram.com",
    "glassdoor.com",
    "github.com",
    "t.co",
    "pinterest.com",
    "tiktok.com",
)

KNOWN_ATS_DOMAINS = (
    "myworkdayjobs.com",
    "boards.greenhouse.io",
    "greenhouse.io",
    "lever.co",
    "smartrecruiters.com",
    "ashbyhq.com",
    "icims.com",
    "phenompeople.com",
    "oraclecloud.com",
    "successfactors.com",
)


def is_valid_job_candidate(
    title: str | None,
    job_url: str | None,
    source_url: str | None = None,
) -> bool:
    """
    Systemic validator enforcing title, domain, and non-job exclusion rules.
    Prevents social media, navigation links, and external chrome text from being treated as jobs.
    """
    if not title or not isinstance(title, str):
        return False

    t_clean = title.strip().lower()
    if len(t_clean) < 3 or t_clean in FORBIDDEN_TITLES:
        return False

    if any(sub in t_clean for sub in FORBIDDEN_SUBSTRINGS):
        return False

    if not job_url or not isinstance(job_url, str):
        return False

    parsed_job = urlparse(job_url.lower())
    netloc = parsed_job.netloc

    # 1. Reject social media domains
    if any(d in netloc for d in SOCIAL_DOMAINS):
        return False

    # 2. Enforce domain boundary if source_url is present
    if source_url:
        src_netloc = urlparse(source_url.lower()).netloc
        src_base = ".".join(src_netloc.split(".")[-2:]) if "." in src_netloc else src_netloc
        net_base = ".".join(netloc.split(".")[-2:]) if "." in netloc else netloc

        is_same_domain = (src_base == net_base) or (src_netloc in netloc or netloc in src_netloc)
        is_ats_domain = any(d in netloc for d in KNOWN_ATS_DOMAINS)

        if not (is_same_domain or is_ats_domain):
            return False

    return True
