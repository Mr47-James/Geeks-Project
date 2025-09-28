html = String.raw;

class TrackCard extends HTMLElement {
  connectedCallback() {
    this.innerHTML = html`
      <a href="${this.getAttribute("trackDetailUrl") || '#'}" class="group relative block bg-black rounded-lg h-full overflow-hidden">
        <img
          alt="${this.getAttribute("title")} album cover"
          src="${this.getAttribute("imageUrl") || `https://picsum.photos/1200/600?random=${this.getAttribute("trackId")}`}"
          class="absolute inset-0 h-full w-full object-cover opacity-75 transition-opacity group-hover:opacity-50"
        />

        <div class="relative p-4 sm:p-6 lg:p-8">
          <p class="text-sm font-medium tracking-widest text-pink-500 uppercase">
            ${this.getAttribute("genre")}
          </p>

          <p class="text-xl font-bold text-white sm:text-2xl">
            ${this.getAttribute("title")}
          </p>
          
          <p class="text-lg text-gray-300 mt-1">
            ${this.getAttribute("artist")}
          </p>

          <div class="mt-32 sm:mt-48 lg:mt-64">
            <div class="translate-y-8 transform opacity-0 transition-all group-hover:translate-y-0 group-hover:opacity-100">
              <p class="text-sm text-white">
                <strong>Album:</strong> ${this.getAttribute("album")}
              </p>
              <p class="text-sm text-white mt-1">
                <strong>Year:</strong> ${this.getAttribute("year")} | <strong>Duration:</strong> ${this.getAttribute("duration")}
              </p>
              <p class="text-sm text-white mt-2">
                <strong>Rating:</strong> ${this.getAttribute("rating")}/10
              </p>
            </div>
          </div>
        </div>
      </a>
    `;
  }
}

customElements.define("track-card", TrackCard);