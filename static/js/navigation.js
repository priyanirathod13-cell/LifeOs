/**
 * LifeOS — Navigation & Sidebar Interactions
 * Handles sidebar collapse, mobile drawer, active nav states, and keyboard accessibility.
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const desktopCollapseBtn = document.getElementById('desktopCollapseBtn');

    // 1. Mobile Drawer Toggle
    function openMobileSidebar() {
      if (sidebar && sidebarBackdrop) {
        sidebar.classList.add('open');
        sidebarBackdrop.classList.add('active');
        document.body.style.overflow = 'hidden';
      }
    }

    function closeMobileSidebar() {
      if (sidebar && sidebarBackdrop) {
        sidebar.classList.remove('open');
        sidebarBackdrop.classList.remove('active');
        document.body.style.overflow = '';
      }
    }

    if (mobileMenuBtn) {
      mobileMenuBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        if (sidebar && sidebar.classList.contains('open')) {
          closeMobileSidebar();
        } else {
          openMobileSidebar();
        }
      });
    }

    if (sidebarBackdrop) {
      sidebarBackdrop.addEventListener('click', closeMobileSidebar);
    }

    // Close mobile sidebar on pressing Escape
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) {
        closeMobileSidebar();
      }
    });

    // Close mobile drawer when clicking a navigation link on mobile
    if (sidebar) {
      const navLinks = sidebar.querySelectorAll('.nav-item');
      navLinks.forEach(function (link) {
        link.addEventListener('click', function () {
          if (window.innerWidth < 992) {
            closeMobileSidebar();
          }
        });
      });
    }

    // 2. Desktop Collapse / Expand with LocalStorage Persistence
    const STORAGE_KEY = 'lifeos_sidebar_collapsed';

    if (desktopCollapseBtn) {
      // Check stored preference
      const isCollapsed = localStorage.getItem(STORAGE_KEY) === 'true';
      if (isCollapsed && window.innerWidth >= 992) {
        document.body.classList.add('sidebar-collapsed');
      }

      desktopCollapseBtn.addEventListener('click', function () {
        document.body.classList.toggle('sidebar-collapsed');
        const currentState = document.body.classList.contains('sidebar-collapsed');
        localStorage.setItem(STORAGE_KEY, currentState.toString());
      });
    }

    // 3. Highlight current route if not already explicitly set in template
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(function (item) {
      const href = item.getAttribute('href');
      if (href && href === currentPath) {
        item.classList.add('active');
      }
    });
  });
})();
