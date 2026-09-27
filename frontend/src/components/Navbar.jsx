function Navbar({ isLoggedIn, onLogout }) {
  return (
    <header className="navbar">
      <div className="navbar__brand">
        <div className="navbar__logo-mark">A</div>

        <div>
          <div className="navbar__title">AUTHENOVA</div>
          <div className="navbar__subtitle">
            AI-Powered Identity Verification
          </div>
        </div>
      </div>

      {isLoggedIn && (
        <div className="navbar__right">
          <div className="navbar__officer">
            <span className="navbar__officer-dot" />
            <span>
              Officer1 <span aria-hidden="true">·</span> Verification Desk
            </span>
          </div>

          <button
            type="button"
            className="btn btn--ghost-dark"
            onClick={onLogout}
          >
            Log Out
          </button>
        </div>
      )}
    </header>
  );
}

export default Navbar;