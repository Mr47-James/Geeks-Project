/**
 * Control Panel JavaScript Module
 * Handles all control panel interactions and API calls
 */

class ControlPanel {
    constructor() {
        this.currentSection = 'profile';
        this.isOpen = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadUserData();
    }

    bindEvents() {
        // Control panel toggle events
        document.addEventListener('click', (e) => {
            // Open control panel from dropdown links
            if (e.target.closest('[onclick*="openProfilePanel"]')) {
                e.preventDefault();
                const section = e.target.closest('[onclick*="openProfilePanel"]').getAttribute('onclick').match(/'([^']+)'/)[1];
                this.open(section);
            }

            // Close control panel when clicking outside (but not on sub-modals)
            if (e.target.classList.contains('control-panel-overlay') && !e.target.closest('.modal-overlay')) {
                this.close();
            }
        });

        // Escape key to close - handle both control panel and modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                // Check if there's a modal open first
                const modal = document.querySelector('.modal-overlay');
                if (modal) {
                    modal.remove();
                } else if (this.isOpen) {
                    this.close();
                }
            }
        });

        // Form submissions
        this.bindFormEvents();
        
        // Toggle switches
        this.bindToggleEvents();
    }

    bindFormEvents() {
        // Profile form
        const profileForm = document.getElementById('profile-form');
        if (profileForm) {
            profileForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveProfile();
            });
        }

        // Security settings
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="change-password"]')) {
                this.showPasswordChangeModal();
            }
            if (e.target.matches('[data-action="manage-sessions"]')) {
                this.showSessionsModal();
            }
        });

        // Payment methods
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="add-payment"]')) {
                this.showAddPaymentModal();
            }
            if (e.target.matches('[data-action="remove-payment"]')) {
                this.removePaymentMethod(e.target.dataset.paymentId);
            }
        });

        // Danger zone actions
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="delete-account"]')) {
                this.showDeleteAccountModal();
            }
        });
    }

    bindToggleEvents() {
        // Handle all toggle switches
        document.addEventListener('change', (e) => {
            if (e.target.matches('.toggle-switch input[type="checkbox"]')) {
                this.handleToggleChange(e.target);
            }
        });
    }

    open(section = 'profile') {
        const overlay = document.getElementById('controlPanel');
        if (overlay) {
            overlay.classList.add('active');
            this.isOpen = true;
            this.showSection(section);
            
            // Close user dropdown
            const dropdown = document.querySelector('.user-dropdown');
            if (dropdown) {
                dropdown.classList.remove('active');
            }
        }
    }

    close() {
        const overlay = document.getElementById('controlPanel');
        if (overlay) {
            overlay.classList.remove('active');
            this.isOpen = false;
        }
    }

    showSection(sectionName) {
        // Hide all sections
        document.querySelectorAll('.control-section').forEach(section => {
            section.classList.remove('active');
        });

        // Remove active class from all nav items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });

        // Show selected section
        const targetSection = document.getElementById(sectionName + '-section');
        if (targetSection) {
            targetSection.classList.add('active');
        }

        // Activate corresponding nav item
        const navItem = document.querySelector(`[onclick*="showControlSection('${sectionName}')"]`);
        if (navItem) {
            navItem.classList.add('active');
        }

        this.currentSection = sectionName;
    }

    async loadUserData() {
        try {
            const response = await fetch('/api/user/profile');
            if (response.ok) {
                const userData = await response.json();
                this.populateUserData(userData);
            }
        } catch (error) {
            console.error('Failed to load user data:', error);
        }
    }

    populateUserData(userData) {
        // Populate profile form
        const usernameField = document.querySelector('#profile-section input[name="username"]');
        const emailField = document.querySelector('#profile-section input[name="email"]');
        const regionField = document.querySelector('#profile-section select[name="region"]');
        const bioField = document.querySelector('#profile-section textarea[name="bio"]');

        if (usernameField) usernameField.value = userData.username || '';
        if (emailField) emailField.value = userData.email || '';
        if (regionField) regionField.value = userData.region || '';
        if (bioField) bioField.value = userData.bio || '';

        // Update avatar
        const avatarCircle = document.querySelector('.avatar-circle');
        if (avatarCircle && userData.avatar_url) {
            avatarCircle.innerHTML = `<img src="${userData.avatar_url}" alt="Avatar" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
        }

        // Populate settings toggles
        this.populateToggleStates(userData.settings || {});
    }

    populateToggleStates(settings) {
        // Security settings
        const twoFAToggle = document.getElementById('2fa-toggle');
        const loginNotificationsToggle = document.getElementById('login-notifications');
        
        if (twoFAToggle) twoFAToggle.checked = settings.two_factor_enabled || false;
        if (loginNotificationsToggle) loginNotificationsToggle.checked = settings.login_notifications !== false;

        // Notification settings
        const emailRecommendations = document.getElementById('email-recommendations');
        const emailDigest = document.getElementById('email-digest');
        const emailSecurity = document.getElementById('email-security');
        const pushReleases = document.getElementById('push-releases');
        const pushPlaylists = document.getElementById('push-playlists');

        if (emailRecommendations) emailRecommendations.checked = settings.email_recommendations !== false;
        if (emailDigest) emailDigest.checked = settings.email_digest !== false;
        if (emailSecurity) emailSecurity.checked = settings.email_security !== false;
        if (pushReleases) pushReleases.checked = settings.push_releases !== false;
        if (pushPlaylists) pushPlaylists.checked = settings.push_playlists || false;

        // Privacy settings
        const shareActivity = document.getElementById('share-activity');
        const dataCollection = document.getElementById('data-collection');

        if (shareActivity) shareActivity.checked = settings.share_activity !== false;
        if (dataCollection) dataCollection.checked = settings.data_collection !== false;
    }

    async saveProfile() {
        const formData = new FormData();
        const profileSection = document.getElementById('profile-section');
        
        // Collect form data
        const username = profileSection.querySelector('input[name="username"]').value;
        const email = profileSection.querySelector('input[name="email"]').value;
        const region = profileSection.querySelector('select[name="region"]').value;
        const bio = profileSection.querySelector('textarea[name="bio"]').value;

        formData.append('username', username);
        formData.append('email', email);
        formData.append('region', region);
        formData.append('bio', bio);

        try {
            const response = await fetch('/api/user/profile', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showNotification('Profile updated successfully!', 'success');
            } else {
                this.showNotification(result.message || 'Failed to update profile', 'error');
            }
        } catch (error) {
            this.showNotification('Network error occurred', 'error');
            console.error('Profile save error:', error);
        }
    }

    async handleToggleChange(toggle) {
        const settingName = toggle.id;
        const isEnabled = toggle.checked;

        try {
            const response = await fetch('/api/user/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    setting: settingName,
                    enabled: isEnabled
                })
            });

            const result = await response.json();
            
            if (!response.ok) {
                // Revert toggle state on error
                toggle.checked = !isEnabled;
                this.showNotification(result.message || 'Failed to update setting', 'error');
            } else {
                this.showNotification(result.message || 'Setting updated', 'success');
            }
        } catch (error) {
            // Revert toggle state on error
            toggle.checked = !isEnabled;
            this.showNotification('Network error occurred', 'error');
            console.error('Setting update error:', error);
        }
    }

    showPasswordChangeModal() {
        const modal = this.createModal('Change Password', `
            <form id="password-change-form">
                <div class="form-group">
                    <label class="form-label">Current Password</label>
                    <input type="password" name="current_password" class="form-control" required>
                </div>
                <div class="form-group">
                    <label class="form-label">New Password</label>
                    <input type="password" name="new_password" class="form-control" required minlength="6">
                </div>
                <div class="form-group">
                    <label class="form-label">Confirm New Password</label>
                    <input type="password" name="confirm_password" class="form-control" required minlength="6">
                </div>
                <div class="section-actions">
                    <button type="submit" class="btn btn-primary">Change Password</button>
                    <button type="button" class="btn btn-glass" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                </div>
            </form>
        `);

        modal.querySelector('#password-change-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.changePassword(new FormData(e.target), modal);
        });
    }

    async changePassword(formData, modal) {
        const newPassword = formData.get('new_password');
        const confirmPassword = formData.get('confirm_password');

        if (newPassword !== confirmPassword) {
            this.showNotification('Passwords do not match', 'error');
            return;
        }

        try {
            const response = await fetch('/api/user/change-password', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showNotification('Password changed successfully!', 'success');
                modal.remove();
            } else {
                this.showNotification(result.message || 'Failed to change password', 'error');
            }
        } catch (error) {
            this.showNotification('Network error occurred', 'error');
            console.error('Password change error:', error);
        }
    }

    showSessionsModal() {
        // Mock session data - replace with real API call
        const sessions = [
            { id: 1, device: 'Chrome on Windows', location: 'New York, US', lastActive: '2 minutes ago', current: true },
            { id: 2, device: 'Safari on iPhone', location: 'New York, US', lastActive: '1 hour ago', current: false },
            { id: 3, device: 'Firefox on Mac', location: 'Los Angeles, US', lastActive: '2 days ago', current: false }
        ];

        const sessionsList = sessions.map(session => `
            <div class="session-item" style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: var(--glass-bg); border-radius: var(--border-radius-sm); margin-bottom: 1rem;">
                <div>
                    <h5 style="margin: 0; color: var(--text-primary);">${session.device} ${session.current ? '(Current)' : ''}</h5>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">${session.location} • ${session.lastActive}</p>
                </div>
                ${!session.current ? `<button class="btn btn-danger btn-sm" onclick="controlPanel.revokeSession(${session.id})">Revoke</button>` : ''}
            </div>
        `).join('');

        this.createModal('Active Sessions', `
            <div class="sessions-list">
                ${sessionsList}
            </div>
            <div class="section-actions">
                <button type="button" class="btn btn-danger" onclick="controlPanel.revokeAllSessions()">Revoke All Other Sessions</button>
                <button type="button" class="btn btn-glass" onclick="this.closest('.modal-overlay').remove()">Close</button>
            </div>
        `);
    }

    async revokeSession(sessionId) {
        try {
            const response = await fetch(`/api/user/sessions/${sessionId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showNotification('Session revoked successfully', 'success');
                // Refresh sessions modal
                document.querySelector('.modal-overlay').remove();
                this.showSessionsModal();
            } else {
                this.showNotification('Failed to revoke session', 'error');
            }
        } catch (error) {
            this.showNotification('Network error occurred', 'error');
        }
    }

    async revokeAllSessions() {
        if (!confirm('Are you sure you want to revoke all other sessions? You will need to log in again on other devices.')) {
            return;
        }

        try {
            const response = await fetch('/api/user/sessions/revoke-all', {
                method: 'POST'
            });

            if (response.ok) {
                this.showNotification('All other sessions revoked successfully', 'success');
                document.querySelector('.modal-overlay').remove();
            } else {
                this.showNotification('Failed to revoke sessions', 'error');
            }
        } catch (error) {
            this.showNotification('Network error occurred', 'error');
        }
    }

    showAddPaymentModal() {
        const modal = this.createModal('Add Payment Method', `
            <form id="payment-form">
                <div class="form-group">
                    <label class="form-label">Card Number</label>
                    <input type="text" name="card_number" class="form-control" placeholder="1234 5678 9012 3456" required>
                </div>
                <div class="form-grid" style="grid-template-columns: 1fr 1fr;">
                    <div class="form-group">
                        <label class="form-label">Expiry Date</label>
                        <input type="text" name="expiry" class="form-control" placeholder="MM/YY" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">CVV</label>
                        <input type="text" name="cvv" class="form-control" placeholder="123" required>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Cardholder Name</label>
                    <input type="text" name="cardholder_name" class="form-control" required>
                </div>
                <div class="section-actions">
                    <button type="submit" class="btn btn-primary">Add Payment Method</button>
                    <button type="button" class="btn btn-glass" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                </div>
            </form>
        `);

        modal.querySelector('#payment-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.addPaymentMethod(new FormData(e.target), modal);
        });
    }

    async addPaymentMethod(formData, modal) {
        try {
            const response = await fetch('/api/user/payment-methods', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showNotification('Payment method added successfully!', 'success');
                modal.remove();
                // Refresh payments section
                this.loadPaymentMethods();
            } else {
                this.showNotification(result.message || 'Failed to add payment method', 'error');
            }
        } catch (error) {
            this.showNotification('Network error occurred', 'error');
            console.error('Payment method error:', error);
        }
    }

    async removePaymentMethod(paymentId) {
        if (!confirm('Are you sure you want to remove this payment method?')) {
            return;
        }

        try {
            const response = await fetch(`/api/user/payment-methods/${paymentId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showNotification('Payment method removed successfully', 'success');
                // Remove the payment card from DOM immediately
                const paymentCard = document.querySelector(`[data-payment-id="${paymentId}"]`).closest('.payment-card');
                if (paymentCard) {
                    paymentCard.style.animation = 'fadeOut 0.3s ease';
                    setTimeout(() => {
                        paymentCard.remove();
                        // Check if no payment methods left
                        const remainingCards = document.querySelectorAll('.payment-section .payment-card');
                        if (remainingCards.length === 0) {
                            this.showEmptyPaymentState();
                        }
                    }, 300);
                }
            } else {
                this.showNotification('Failed to remove payment method', 'error');
            }
        } catch (error) {
            this.showNotification('Network error occurred', 'error');
        }
    }

    showEmptyPaymentState() {
        const paymentSection = document.querySelector('.payment-section');
        if (paymentSection) {
            const existingCards = paymentSection.querySelectorAll('.payment-card');
            existingCards.forEach(card => card.remove());
            
            const emptyState = document.createElement('div');
            emptyState.className = 'empty-payment-state';
            emptyState.style.cssText = `
                text-align: center;
                padding: 2rem;
                color: var(--text-secondary);
                font-style: italic;
            `;
            emptyState.innerHTML = '<p>No payment methods added yet.</p>';
            
            const addButton = paymentSection.querySelector('[data-action="add-payment"]');
            if (addButton) {
                paymentSection.insertBefore(emptyState, addButton.parentElement);
            }
        }
    }

    async loadPaymentMethods() {
        try {
            const response = await fetch('/api/user/payment-methods');
            if (response.ok) {
                const paymentMethods = await response.json();
                this.updatePaymentMethodsDisplay(paymentMethods);
            }
        } catch (error) {
            console.error('Failed to load payment methods:', error);
        }
    }

    updatePaymentMethodsDisplay(paymentMethods) {
        const paymentSection = document.querySelector('.payment-section');
        if (!paymentSection) return;

        // Clear existing content except the title and add button
        const existingCards = paymentSection.querySelectorAll('.payment-card, .empty-payment-state');
        existingCards.forEach(card => card.remove());

        if (paymentMethods.length === 0) {
            this.showEmptyPaymentState();
            return;
        }

        const methodsHTML = paymentMethods.map(method => `
            <div class="payment-card">
                <div class="card-info">
                    <i class="fab fa-cc-${method.brand.toLowerCase()}"></i>
                    <div>
                        <div>•••• •••• •••• ${method.last4}</div>
                        <div class="card-expiry">Expires ${method.expiry}</div>
                    </div>
                </div>
                <button class="btn btn-glass btn-sm" data-action="remove-payment" data-payment-id="${method.id}">Remove</button>
            </div>
        `).join('');

        const addButton = paymentSection.querySelector('[data-action="add-payment"]').parentElement;
        addButton.insertAdjacentHTML('beforebegin', methodsHTML);
    }

    showDeleteAccountModal() {
        const modal = this.createModal('Delete Account', `
            <div style="text-align: center; padding: 1rem;">
                <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: #EE5A24; margin-bottom: 1rem;"></i>
                <h3 style="color: var(--text-primary); margin-bottom: 1rem;">Are you absolutely sure?</h3>
                <p style="color: var(--text-secondary); margin-bottom: 2rem;">
                    This action cannot be undone. This will permanently delete your account, 
                    all your playlists, preferences, and remove all your data from our servers.
                </p>
                <form id="delete-account-form">
                    <div class="form-group">
                        <label class="form-label">Type "DELETE" to confirm:</label>
                        <input type="text" name="confirmation" class="form-control" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Enter your password:</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <div class="section-actions">
                        <button type="submit" class="btn btn-danger">Delete My Account</button>
                        <button type="button" class="btn btn-glass" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                    </div>
                </form>
            </div>
        `);

        modal.querySelector('#delete-account-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.deleteAccount(new FormData(e.target), modal);
        });
    }

    async deleteAccount(formData, modal) {
        const confirmation = formData.get('confirmation');
        
        if (confirmation !== 'DELETE') {
            this.showNotification('Please type "DELETE" to confirm', 'error');
            return;
        }

        try {
            const response = await fetch('/api/user/delete-account', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showNotification('Account deleted successfully. Redirecting...', 'success');
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
            } else {
                this.showNotification(result.message || 'Failed to delete account', 'error');
            }
        } catch (error) {
            this.showNotification('Network error occurred', 'error');
            console.error('Account deletion error:', error);
        }
    }

    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: var(--bg-overlay);
            backdrop-filter: blur(10px);
            z-index: 3000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        modal.innerHTML = `
            <div class="modal-container" style="
                background: var(--glass-bg);
                backdrop-filter: var(--glass-backdrop);
                border: 1px solid var(--glass-border);
                border-radius: var(--border-radius);
                box-shadow: var(--glass-shadow);
                max-width: 500px;
                width: 90%;
                max-height: 80vh;
                overflow-y: auto;
            ">
                <div class="modal-header" style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 1.5rem;
                    border-bottom: 1px solid var(--glass-border);
                ">
                    <h3 style="margin: 0; color: var(--text-primary);">${title}</h3>
                    <button class="modal-close" style="
                        background: none;
                        border: none;
                        color: var(--text-primary);
                        font-size: 1.5rem;
                        cursor: pointer;
                        padding: 0;
                        width: 30px;
                        height: 30px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border-radius: 50%;
                        transition: background 0.3s ease;
                    " onclick="this.closest('.modal-overlay').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-content" style="padding: 1.5rem;">
                    ${content}
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });

        return modal;
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `flash-message ${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            z-index: 4000;
            max-width: 400px;
            animation: slideInRight 0.3s ease;
        `;

        const icons = {
            success: 'check-circle',
            error: 'times-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };

        notification.innerHTML = `
            <i class="fas fa-${icons[type] || icons.info}"></i>
            ${message}
        `;

        document.body.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.style.animation = 'slideInRight 0.3s ease reverse';
            setTimeout(() => notification.remove(), 300);
        }, 5000);

        // Click to remove
        notification.addEventListener('click', () => {
            notification.remove();
        });
    }
}

// Global functions for backward compatibility
function openProfilePanel(section) {
    if (window.controlPanel) {
        window.controlPanel.open(section);
    }
}

function closeControlPanel() {
    if (window.controlPanel) {
        window.controlPanel.close();
    }
}

function showControlSection(section) {
    if (window.controlPanel) {
        window.controlPanel.showSection(section);
    }
}

// Initialize control panel when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.controlPanel = new ControlPanel();
});