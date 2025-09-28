html = String.raw;

class Navbar extends HTMLElement {
  connectedCallback() {
    this.innerHTML = html`
      <nav class="harmony-bg p-4 backdrop-blur-sm sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4">
          <div class="flex items-center justify-between">
            <a href="/" class="text-white text-2xl font-bold flex items-center">
              <i class="fas fa-music mr-2"></i>
              Harmony
            </a>

            <div class="flex items-center space-x-4">
              <a href="/tracks" class="text-white hover:text-harmony-accent transition-colors">
              </a>
              <a href="/artists" class="text-white hover:text-harmony-accent transition-colors">
              </a>
              <a href="/new" class="text-white hover:text-gray-300">
                <button class="btn-harmony px-4 py-2 rounded flex items-center">
                  <i class="fas fa-plus-circle mr-2"></i>
                  Add Track
                </button>
              </a>
            </div>
          </div>
        </div>
      </nav>
    `;
  }
}

customElements.define("navbar-component", Navbar);