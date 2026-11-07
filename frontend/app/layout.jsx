import "./globals.css";

export const metadata = {
  title: "ClaimShield Desk",
  description: "Denial-defense and pre-dispatch scrubber for hospital TPA desks. All cases SYNTHETIC.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("claimshield-theme");if(t!=="light"&&t!=="dark")t="dark";document.documentElement.dataset.theme=t;}catch(e){document.documentElement.dataset.theme="dark";}})();`,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
