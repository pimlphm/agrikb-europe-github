# AgriKB Europe

English, Europe-focused static presentation site for an AgriKB smart-agriculture pilot.

## What This Contains

- `index.html` - standalone presentation website
- `assets/screenshots/` - generated English mock screenshots
- `package.json` - local preview scripts
- `.github/workflows/pages.yml` - optional GitHub Pages deployment workflow

## Local Preview

```bash
npm run serve
```

Then open the printed local URL.

No build step is required. The site is static and can be published directly from the repository root.

## GitHub Pages Publishing

1. Create a new GitHub repository.
2. Upload or push this folder.
3. In GitHub, enable Pages from GitHub Actions.
4. The included workflow deploys the repository root.

## European Source Aggregation References

The source aggregation mockup is designed around public European agriculture information sources:

- European Commission DG AGRI: https://agriculture.ec.europa.eu/
- EU CAP Network: https://eu-cap-network.ec.europa.eu/
- Copernicus Land Monitoring Service: https://land.copernicus.eu/
- Eurostat Agriculture: https://ec.europa.eu/eurostat/web/agriculture
- EFSA: https://www.efsa.europa.eu/
- EUMETSAT: https://www.eumetsat.int/
- EUR-Lex: https://eur-lex.europa.eu/
- National market portals such as FranceAgriMer: https://www.franceagrimer.fr/

These references are illustrative for the presentation; production integrations should verify licensing, API availability and data-refresh requirements.
