async function compartir(url) {
    const title = document.title;
    if (navigator.share) {
        try {
            await navigator.share({ title, url });
            console.log("Enlace compartido con éxito / Link shared successfully");
        } catch (err) { console.error("Errorr:", err); }
    } else {
        try {
            await navigator.clipboard.writeText(url);
            alert("URL copied / URL copiada:\n" + url);
        } catch (err) {
            console.error("Error:", err);
            alert("No se pudo copiar la URL / Couldn't copy URL");
        }
    }
}
