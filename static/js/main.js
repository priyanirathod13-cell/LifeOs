/**
 * LifeOS — Core Frontend Utilities & Component Interactions
 * Handles dropdowns, modals, alerts, and interactive components.
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    // ========================================================================
    // 1. DROPDOWN COMPONENT
    // ========================================================================
    const dropdownToggles = document.querySelectorAll('[data-dropdown-toggle]');

    dropdownToggles.forEach(function (toggle) {
      toggle.addEventListener('click', function (e) {
        e.stopPropagation();
        const targetId = this.getAttribute('data-dropdown-toggle');
        const menu = document.getElementById(targetId);

        // Close other open dropdowns
        document.querySelectorAll('.dropdown-menu.show').forEach(function (openMenu) {
          if (openMenu !== menu) {
            openMenu.classList.remove('show');
          }
        });

        if (menu) {
          menu.classList.toggle('show');
          const isExpanded = menu.classList.contains('show');
          toggle.setAttribute('aria-expanded', isExpanded);
        }
      });
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', function () {
      document.querySelectorAll('.dropdown-menu.show').forEach(function (menu) {
        menu.classList.remove('show');
      });
      dropdownToggles.forEach(function (toggle) {
        toggle.setAttribute('aria-expanded', 'false');
      });
    });

    // ========================================================================
    // 2. MODAL COMPONENT
    // ========================================================================
    let lastActiveElement = null;

    function openModal(modalId) {
      const modal = document.getElementById(modalId);
      if (modal) {
        lastActiveElement = document.activeElement;
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';

        // Focus first actionable element inside modal
        const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        if (focusable.length) {
          focusable[0].focus();
        }
      }
    }

    function closeModal(modal) {
      if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
        if (lastActiveElement) {
          lastActiveElement.focus();
        }
      }
    }

    // Modal Triggers
    const modalOpenTriggers = document.querySelectorAll('[data-modal-target]');
    modalOpenTriggers.forEach(function (trigger) {
      trigger.addEventListener('click', function (e) {
        e.preventDefault();
        const modalId = this.getAttribute('data-modal-target');
        openModal(modalId);
      });
    });

    // Modal Close Buttons
    const modalCloseTriggers = document.querySelectorAll('[data-modal-close]');
    modalCloseTriggers.forEach(function (trigger) {
      trigger.addEventListener('click', function (e) {
        e.preventDefault();
        const modal = this.closest('.modal-backdrop');
        closeModal(modal);
      });
    });

    // Close modal when clicking directly on backdrop
    const modalBackdrops = document.querySelectorAll('.modal-backdrop');
    modalBackdrops.forEach(function (backdrop) {
      backdrop.addEventListener('click', function (e) {
        if (e.target === this) {
          closeModal(this);
        }
      });
    });

    // ========================================================================
    // 3. ALERT / NOTIFICATION DISMISS
    // ========================================================================
    const alertCloseButtons = document.querySelectorAll('.alert-close-btn');
    alertCloseButtons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        const alertBox = this.closest('.alert');
        if (alertBox) {
          alertBox.style.opacity = '0';
          alertBox.style.transform = 'translateY(-4px)';
          alertBox.style.transition = 'all 180ms ease';
          setTimeout(function () {
            alertBox.remove();
          }, 180);
        }
      });
    });

    // ========================================================================
    // 4. GLOBAL ESCAPE KEY HANDLER
    // ========================================================================
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        // Close modals
        const activeModal = document.querySelector('.modal-backdrop.show');
        if (activeModal) {
          closeModal(activeModal);
        }
        // Close dropdowns
        document.querySelectorAll('.dropdown-menu.show').forEach(function (menu) {
          menu.classList.remove('show');
        });
      }
    });

    // Expose LifeOS UI Helpers to window for programmatic control
    window.LifeOS = {
      openModal: openModal,
      closeModal: closeModal
    };
  });
})();
