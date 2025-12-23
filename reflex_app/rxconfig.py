import reflex as rx

config = rx.Config(
    app_name="reflex_app",
    title="Detective Board - Investigation Visualization",
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
    frontend_port=3003,
    backend_port=8003,
)
