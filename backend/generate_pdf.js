const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    // Load the HTML file
    const fileUrl = 'file:///' + path.resolve('C:/Users/avenxkat/.gemini/antigravity/brain/99b6d637-87d5-449f-aef2-d39f29d6eb33/architecture_overview.html').replace(/\\/g, '/');
    await page.goto(fileUrl, { waitUntil: 'networkidle0' });
    
    // Wait for Mermaid to render (look for SVG inside .mermaid divs)
    await page.waitForFunction(() => {
        const mermaids = document.querySelectorAll('.mermaid');
        for (let m of mermaids) {
            if (!m.querySelector('svg')) return false;
        }
        return true;
    });

    // Output PDF to the artifacts directory
    const outPath = path.resolve('C:/Users/avenxkat/.gemini/antigravity/brain/99b6d637-87d5-449f-aef2-d39f29d6eb33/Team_Kapture_Architecture.pdf');
    await page.pdf({
        path: outPath,
        format: 'A4',
        printBackground: true,
        margin: { top: '20px', right: '20px', bottom: '20px', left: '20px' }
    });

    console.log('PDF generated at:', outPath);
    await browser.close();
})();
