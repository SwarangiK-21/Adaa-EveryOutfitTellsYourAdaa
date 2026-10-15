import React from 'react';

export default function Heading({ eyebrow, title, sub, action }) {
  return (
    <div className="heading">
      <div><small>{eyebrow}</small><h1>{title}</h1><p>{sub}</p></div>
      {action}
    </div>
  );
}
